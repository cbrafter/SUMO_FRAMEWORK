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
import re
from glob import glob
import os
from scipy.spatial import distance
import numpy as np


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


def getIntergreenTime(junctionID):
    juncPos = traci.junction.getPosition(junctionID)
    edges = traci.trafficlights.getControlledLinks(junctionID)
    edges = [x for z in edges for y in z for x in y[:2]]
    edges = list(set(edges))
    boundingCoords = []
    for edge in edges:
        dMin, coordMin = 1e6, []
        for laneCoord in traci.lane.getShape(edge):
            dist = getDistance(juncPos, laneCoord)
            if dist < dMin:
                dMin, coordMin = dist, laneCoord
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

def getRouteDict():
    fileNames = glob('../2_models/VALIDROUTES/*.rou.xml')
    models = []
    regex = re.compile('.+edges="(.+?)"')
    routeDict = {}

    for fileName in fileNames:
        file = open(fileName, 'r')
        model = os.path.basename(fileName).split('_')[0]
        routeDict[model] = []
        for line in file:
            match = regex.match(line)
            if not match:
                continue
            else:
                routeDict[model].append(match.groups()[0].split())
        file.close()

    return routeDict

def isInRange(vehPosition, scanRange, jcnGeometry):
    center, JCR = jcnGeometry # jcnPos, jcnCtrlRegion
    distance = hypot(*(vehPosition - center))
    c1 = distance < scanRange
    # shorten variable name and check box is in bounds
    c2 = JCR['W'] <= vehPosition[0] <= JCR['E']
    c3 = JCR['S'] <= vehPosition[1] <= JCR['N']
    return (c1 and c2 and c3)


# default dict that finds and remembers road speed limits (only if static)
# needs to be updated otherwise
class speedLimDict(defaultdict):
    def __missing__(self, key):
        self[key] = traci.lane.getMaxSpeed(key)
        return self[key]

# defaultdict that finds and remembers vehicle types (only if static)
# needs to be updated otherwise
class vTypeDict(defaultdict):
    def __missing__(self, key):
        self[key] = traci.vehicle.getTypeID(key)
        return self[key]

def getDistance(A, B):
    x1, y1 = A
    x2, y2 = B
    return hypot(x1-x2, y1-y2)

def flatten(ListofLists):
    return [x for y in ListofLists for x in y]