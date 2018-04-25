# -*- coding: utf-8 -*-
"""
Created on Fri Mar 16 12:04:15 2018

@author: craig
"""

import os
import sys
tools = os.path.join('/usr/share/sumo', 'tools')
sys.path.append(tools)
import sumolib
import numpy as np
import math
from scipy.spatial import distance


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


net = sumolib.net.readNet('../2_models/corridor/corridor.net.xml')
tls = [n for n in net.getNodes() if n.getType() == 'traffic_light']
tlsDist = {}
for tl in tls:
    x1, y1 = tl.getCoord()  # tl center
    edges = tl.getIncoming() + tl.getOutgoing()
    boundingCoords = []
    # find edge closest to center
    for edge in edges:
        dMin, coordMin = 1e6, []
        for x2, y2 in edge.getShape():
            dist = math.hypot(x2-x1, y2-y1)
            if dist < dMin:
                dMin, coordMin = dist, [x2, y2]
        boundingCoords.append(coordMin)
    # get max of closest edge pairwise distances
    dMax = np.max(distance.cdist(boundingCoords, boundingCoords))
    print(tl.getID(), dMax, getIntergreen(dMax))
    tlsDist = {tl.getID(): dMax}
