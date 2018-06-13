# -*- coding: utf-8 -*-
"""
A script that generates loops for junctions incoming lanes at positions X1 to Xn

Usage
-----
python insertODLoops.py model.net.xml X1 X2 ... Xn

Output
------
loops.det.xml : XML file
    An 'additional' file containing the loop definitions

author: Craig B. Rafter
mailto: c.b.rafter@soton.ac.uk
date: 01/09/2017
copyright: GNU GPL v3.0 - attribute me if used
"""

from __future__ import print_function
from __future__ import absolute_import
import os
import sys
SUMO_HOME = '/usr/share/sumo'
sys.path.append(os.path.join(SUMO_HOME, 'tools'))
import sumolib

# import net file
netfilename = sys.argv[1]
# netfilename = './civicCentre/civicCentre.net.xml'

net = sumolib.net.readNet(netfilename)
incomingLanes = []
incomingLoopLoc = []
outgoingLanes = []
trafficLights = [n for n in net.getNodes() if 'junc' in n.getID()]

# get traffic lights
for TL in trafficLights:
    # get connections
    for edge in TL.getIncoming():
        for lane in edge.getLanes():
            incomingLanes.append(lane.getID())
            incomingLoopLoc.append(1)
    for edge in TL.getOutgoing():
        for lane in edge.getLanes():
            outgoingLanes.append(lane.getID())

# Get unique input lanes
incomingLanes = list(set(incomingLanes))
outgoingLanes = list(set(outgoingLanes))

# write loops to file
loopfilename = 'loops.det.xml'
loopfile = open(loopfilename, 'w')
loopfile.write('<?xml version="1.0"?>\n<additional>')
loopID = 0
for lane, loc in zip(incomingLanes,incomingLoopLoc):
    loopfile.write('\t<inductionLoop id="in{}" lane="{}" pos="{}" freq="1800" file="loops.out"/>\n'.format(loopID, lane, loc))
    loopID += 1
for lane in outgoingLanes:
    loopfile.write('\t<inductionLoop id="out{}" lane="{}" pos="1" freq="1800" file="loops.out"/>\n'.format(loopID, lane))
    loopID += 1

loopfile.write('</additional>\n')
loopfile.close()
