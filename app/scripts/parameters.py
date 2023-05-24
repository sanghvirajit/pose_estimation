#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Parameters

    @author: Rajit. S
"""

def getKeypoints():
    # Selecting the keypoints to display
    return [0, 2, 5, 7, 8, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32]

def getConnections():
    # New connections for selected keypoints
    # 2 new keypoints, #33 shoulder mid, #34 Hip mid
    return frozenset({ 
                                    (0, 2),
                                    (0, 33),
                                    (0, 5),
                                    (2, 7),
                                    (5, 8),
                                    (11, 33),
                                    (33, 12),
                                    (11, 13),
                                    (11, 23),
                                    (12, 14),
                                    (12, 24),
                                    (13, 15),
                                    (14, 16),
                                    (23, 34),
                                    (34, 24),
                                    (23, 25),
                                    (24, 26),
                                    (25, 27),
                                    (26, 28),
                                    (27, 29),
                                    (27, 31),
                                    (28, 30),
                                    (28, 32),
                                    (29, 31),
                                    (30, 32),
                                    (33, 34)
                            })
