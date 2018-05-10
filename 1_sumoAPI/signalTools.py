#!/usr/bin/env python
"""
@file    signalTools.py
@author  Craig Rafter
@date    09/05/2018

class for fixed time signal control
"""

import traci
from collections import defaultdict
from math import atan2, degrees, ceil, hypot


def getIntergreen(dist):
    # <10 & 10-18 & 19-27 & 28-37 & 38-46 & 47-55 & 56-64 & >65
    #  5  &   6   &   7   &   8   &   9   &  10   &  11   & 12
    diamThresholds = [10, 19, 28, 38, 47, 56, 65]
    intergreen = 5
    for threshold in diamThresholds:
        if dist < threshold:
            return intergreen
        else:
            intergreen += 1
    return intergreen


def getIntergreenTime(self, junctionID):
    x1, y1 = traci.junction.getPosition(junctionID)
    edges = traci.trafficlights.getControlledLinks(junctionID)
    edges = [x for z in edges for y in z for x in y[:2]]
    edges = list(set(edges))
    boundingCoords = []
    for edge in edges:
        dMin, coordMin = 1e6, []
        for x2, y2 in traci.lane.getShape(edge):
            dist = math.hypot(x2-x1, y2-y1)
            if dist < dMin:
                dMin, coordMin = dist, [x2, y2]
        boundingCoords.append(coordMin)
    # get max of closest edge pairwise distances
    dMax = np.max(distance.cdist(boundingCoords, boundingCoords))
    return getIntergreen(dMax)


def getSUMOHeading(currentLoc, prevLoc):
    dy = currentLoc[1] - prevLoc[1]
    dx = currentLoc[0] - prevLoc[0]
    if currentLoc[1] == prevLoc[1] and currentLoc[0] == prevLoc[0]:
        heading = -1
    else:
        if dy >= 0:
            heading = degrees(atan2(dy, dx))
        else:
            heading = 360 + degrees(atan2(dy, dx))
    
    # Map angle to make compatible with SUMO heading
    if 0 <= heading <= 90:
        heading = 90 - heading
    elif 90 < heading < 360:
        heading = 450 - heading

    return heading


def unique(sequence):
    return list(set(sequence))


def mean(x):
    return sum(x)/float(len(x))


def getIncomingLaneInfo(controlledLanes):
    laneInfo = defaultdict(list) 
    for lane in unique(controlledLanes):
        shape = traci.lane.getShape(lane)
        width = traci.lane.getWidth(lane)
        heading = getSUMOHeading(shape[1], shape[0])
        x1, y1 = shape[0]
        x2, y2 = shape[1]
        dx = abs(x2 - x1) 
        dy = abs(y2 - y1)
        if dx > dy:
            y1 += width
            y2 -= width
        else: 
            x1 += width
            x2 -= width
        laneInfo[lane] = {'heading': heading, 
                          'bounds': {'x1': x1, 'y1': y1,
                                     'x2': x2, 'y2': y2}
                         }

    return laneInfo