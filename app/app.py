#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" FastAPI for Orthelligent app
    
    @author: Rajit. S
"""

import asyncio
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Annotated

import boto3
import botocore
import cv2 as cv
import environs
import time

from fastapi import Depends, FastAPI
from smart_open import open
from vidgear.gears import VideoGear

from app.scripts.detector import PoseDetector
from app.scripts.parameters import getConnections, getKeypoints

env = environs.Env()

# initialize a shared executor to limit concurrency and control memory usage of the whole server
executor = ThreadPoolExecutor(env.int("THREADS", 4))
keypoints = getKeypoints()
connections = getConnections()

# load the ML model into memory once on startup (for performance)
detector = PoseDetector()

app = FastAPI()

# thread-safe s3 client
# set credentials as
# AWS_ACCESS_KEY_ID=...
# AWS_SECRET_ACCESS_KEY=...
s3_client = boto3.session.Session().client(
    "s3",
    config=botocore.client.Config(
        max_pool_connections=env.int("AWS_S3_CONNECTIONS", 100),
        tcp_keepalive=env.bool("AWS_TCP_KEEPALIVE", True),
        retries={
            "max_attempts": env.int("AWS_MAX_ATTEMPTS", 6),
            "mode": env("AWS_RETRY_MODE", "adaptive"),
        },
    ),
    # https://docs.ionos.com/cloud/managed-services/s3-object-storage/endpoints
    region_name=env("AWS_DEFAULT_REGION", "de"),
    endpoint_url=env("AWS_ENDPOINT_URL", "https://s3-eu-central-1.ionoscloud.com"),
)
# configure open to handle the `s3://` protocol
open = partial(open, transport_params={"client": s3_client})  # noqa:A001


@app.get("/")
def endpoint():
    return {"Hallo! Willkommen bei Orthelligent Vision Test Version!"}


def stream_uri(uri_in, uri_out, chunk_size=1 << 18):  # 256kB chunks
    """Write from uri_in to uri_out with minimal memory footprint ref https://stackoverflow.com/a/76235280/5511061."""
    with open(uri_in, "rb") as fin, open(uri_out, "wb") as fout:
        while chunk := fin.read(chunk_size):
            fout.write(chunk)


async def temp_path(suffix=".mp4"):
    """Create (and finally delete) a temporary file in a safe and non-blocking fashion ref https://stackoverflow.com/a/76251003/5511061."""
    loop = asyncio.get_running_loop()
    _, path = await loop.run_in_executor(None, tempfile.mkstemp, suffix)
    try:
        yield path
    finally:
        await loop.run_in_executor(None, os.unlink, path)


def render_frame(original_frame):
    """Detect pose in a frame and render the output frame."""
    # Getting the output
    frame, pose_landmarks, _ = detector.findPose(original_frame)

    # Getting the positions of the landmarks (x, y, z)
    _, landmarks_List = detector.getLandmarkCoordinates(frame, pose_landmarks)

    if not landmarks_List:
        return original_frame

    # Keeping only the interested keypoints
    new_landmarks = {k: landmarks_List[k] for k in keypoints if k in landmarks_List}

    # Calculate shoulder mid Key point (extra keypoint)
    new_landmarks[33] = (
        int((new_landmarks[11][0] + new_landmarks[12][0]) * 0.5),
        int((new_landmarks[11][1] + new_landmarks[12][1]) * 0.5),
    )

    # Calculate hip mid Key point (extra keypoint)
    new_landmarks[34] = (
        int((new_landmarks[23][0] + new_landmarks[24][0]) * 0.5),
        int((new_landmarks[23][1] + new_landmarks[24][1]) * 0.5),
    )

    # Drawing Keypoints and landmarks on image
    detector.drawLandmarks(frame, new_landmarks, connections)

    return frame


def process_video(path_in: str, path_out: str, height_cm: float):
    """Loop over path_in video and write the processed video to path_out."""

    start = time.time()

    input_stream = VideoGear(source=path_in).start()
    data_fps = input_stream.framerate

    # load one frame to peek the resolution
    first_frame = input_stream.read()
    data_height, data_width, _ = first_frame.shape

    # write to a temporary file
    fourcc = cv.VideoWriter_fourcc("m", "p", "4", "v")
    writer = cv.VideoWriter(path_out, fourcc, data_fps, (data_width, data_height))

    # render the first frame
    writer.write(render_frame(first_frame))

    # render the rest of the frames
    while (original_frame := input_stream.read()) is not None:
        writer.write(render_frame(original_frame))

    # clean up
    writer.release()
    input_stream.stop()

    end = time.time()

    inference_time = end-start

    payload = {"inference_time": inference_time}

    return payload


# if the input is https://.../file.mp4, only the analysis parameters are returned
# if the input is s3://.../file.mp4, an s3_uri will be added to the payload pointing to the processed video
# either:
# curl localhost:80/gait?video=https://ik.imagekit.io/demo/sample-video.mp4&height_cm=185.5
# or:
# curl localhost:80/gait?video=s3://bucket/video.mp4&height_cm=185.5
@app.get("/gait")
async def gait(
    video: str,
    height_cm: float,
    path_in: Annotated[str, Depends(temp_path, use_cache=False)],
    path_out: Annotated[str, Depends(temp_path, use_cache=False)],
):
    """Generate a GAIT analysis video and stream it back to the client."""
    loop = asyncio.get_running_loop()
    # write the video to path_in tempfile (not cpu-bound, can use the default executor)
    await loop.run_in_executor(None, stream_uri, video, path_in)
    # process path_in and write to path_out (concurrency limited by our shared executor)
    payload = await loop.run_in_executor(
        executor, process_video, path_in, path_out, height_cm
    )

    # only upload to s3 if the input was also s3
    if video.startswith("s3://"):
        # upload path_out to s3 and add the path to the json payload
        path_out_s3 = f"{video[:-4]}_processed.mp4"
        await loop.run_in_executor(None, stream_uri, path_out, path_out_s3)
        payload["video"] = path_out_s3

    # return json payload
    return payload
