#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Detector Class

    @author: Rajit. S
"""

import mediapipe as mp
import cv2 as cv
import threading

class PoseDetector:

    def __init__(self,
               static_image_mode=False,
               model_complexity=2, # 0 for pose_landmark_lite.tflite, 1 for pose_landmark_full.tflite, 2 for pose_landmark_heavy.tflite
               smooth_landmarks=True,
               enable_segmentation=False,
               smooth_segmentation=True,
               min_detection_confidence=0.5,
               min_tracking_confidence=0.5):

        self.mode = static_image_mode
        self.complexity = model_complexity
        self.smooth_landmarks = smooth_landmarks
        self.segmentation = enable_segmentation
        self.smooth_segmentation = smooth_segmentation
        self.detectionCon = min_detection_confidence
        self.trackCon = min_tracking_confidence
        self.pelvic_tilt = []
        self.pelvic_obliquity= []
        self.pelvic_rotation = []
        self.lock = threading.Lock()

        # Initializing mediapipe pose class.
        self.mpPose = mp.solutions.pose

        # Setting up the Pose function.
        self.pose = self.mpPose.Pose(self.mode, self.complexity, self.smooth_landmarks, self.segmentation, self.smooth_segmentation, self.detectionCon, self.trackCon)

    def findPose(self, frame):

        '''
            This function indentifies the Pose in the Image.
            Args:
                frame: np.ndarray
            Returns:
                It returns Image, list of landmarks and connections in the Image.
        '''

        #frameRBG = cv.cvtColor(frame, cv.COLOR_BGR2RGB)

        # this call is not thread-safe, make sure it runs sequentially
        with self.lock:
            # Getting the results
            results = self.pose.process(frame)
        
        return frame, results.pose_landmarks, self.mpPose.POSE_CONNECTIONS

    def getLandmarkCoordinates(self, frame, pose_landmarks):

        '''
            This function returns the position of the keypoints.
            Args:
                frame: np.ndarray
            Returns:
                normalized and unnormalized (X, Y) coordinates of the keypoints
        '''

        idx_to_coordinates_normalized = {}
        idx_to_coordinates_unnormalized = {}
        if pose_landmarks:
            for id, lm in enumerate(pose_landmarks.landmark):
                h, w, c = frame.shape
                cx, cy, cz = int(lm.x * w), int(lm.y * h), int(lm.z * w)
                idx_to_coordinates_unnormalized[id] = (cx, cy, cz)
                idx_to_coordinates_normalized[id] = (lm.x, lm.y, lm.z)
                
        return idx_to_coordinates_normalized, idx_to_coordinates_unnormalized
        
    def drawLandmarks(self, frame, landmarks_List, PoseConnection):
        
        '''
            This function draw landmarks and connections on the image.
            Args:
                frame: np.ndarray
                landmark list: list of landmarks with coordinates.
                Connections: set of connections.
        '''

        for connections in PoseConnection:
            
            # Getting the ids from frozen set of connections
            idFrom = connections[0]
            idTo = connections[1]
                    
            if idFrom in landmarks_List and idTo in landmarks_List:

                # Drawing the pose
                cv.line(frame, (landmarks_List[idFrom][0], landmarks_List[idFrom][1]), (landmarks_List[idTo][0], landmarks_List[idTo][1]), (0, 0, 255), 2)

                # Drawing the key points 
                cv.circle(frame, (landmarks_List[idFrom][0], landmarks_List[idFrom][1]), 5, (255, 255, 255), -1)
                cv.circle(frame, (landmarks_List[idTo][0], landmarks_List[idTo][1]), 5, (255, 255, 255), -1)

                cv.circle(frame, (landmarks_List[idFrom][0], landmarks_List[idFrom][1]), 10, (255, 255, 255), 2)
                cv.circle(frame, (landmarks_List[idTo][0], landmarks_List[idTo][1]), 10, (255, 255, 255), 2)
