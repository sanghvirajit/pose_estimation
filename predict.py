#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Serve model as a FastAPI application
    Testing the Local/Cloud Endpoint

    @author: Rajit. S
"""

from concurrent.futures import ThreadPoolExecutor
import requests

urls = {
    "local": "http://localhost:80/gait",
    "cloud": "https://orthelligent.livelyriver-f6a1dec7.germanywestcentral.azurecontainerapps.io/gait"
}


def get(session: requests.Session, server_url: str, video_url: str, height_cm: float):
    resp = session.get(server_url, params={"video": video_url, "height_cm": height_cm})
    resp.raise_for_status()
    print(resp.json())


# bomb the endpoint with concurrent requests
num_requests = 100
session = requests.Session()  # https://stackoverflow.com/a/66672380/5511061
session.mount("https://", requests.adapters.HTTPAdapter(pool_maxsize=num_requests))
with ThreadPoolExecutor() as executor:
    for i in range(num_requests):
        executor.submit(
            get,
            session=session,
            server_url=urls["cloud"],
            video_url="https://ik.imagekit.io/demo/sample-video.mp4",
            height_cm=185.5
        )

