# -*- coding: utf-8 -*-
"""
A script that generates loops at the network fringes. 
Edit the distanceFromFringe parameter in the to adjust the distance from fringe
edge.
Edit freq to adjust the aggregation perisod in seconds.
Edit ofile to set the output data file

Usage
-----
python insertODLoops.py model.net.xml

Output
------
ODloops.det.xml : XML file
    An 'additional' file containing the loop definitions

author: Craig B. Rafter
mailto: c.b.rafter@soton.ac.uk
date: 01/09/2017
copyright: GNU GPL v3.0 - attibute me if used
"""

from __future__ import print_function
from __future__ import absolute_import
import os
import sys
SUMO_HOME = '/usr/share/sumo'
sys.path.append(os.path.join(SUMO_HOME, 'tools'))
import sumolib

# Script parameters
distanceFromFringe = 5
freq = 300 # 5 min aggregate
ofile = 'ODloops.det.xml'

# import net file
netfilename = sys.argv[1]
net = sumolib.net.readNet(netfilename)
startEdges = []
endEdges = []

# find the fringe edges and see if it's a starting/ending edge
for edge in net.getEdges():
    if edge.is_fringe() and not len(edge.getIncoming()):
        startEdges.append(edge)
    elif edge.is_fringe() and not len(edge.getOutgoing()):
        endEdges.append(edge)
    else:
        continue

# write loops to file
loopfilename = 'ODloops.det.xml'
loopfile = open(loopfilename, 'w')
loopfile.write("""<?xml version="1.0"?>
<additional>
""")
loopID = 0
for edge in startEdges:
    edgeLen = edge.getLength()
    loc = distanceFromFringe - edgeLen
    Nlanes = len(edge.getLanes())
    laneIDs = [edge.getID()+'_'+str(x) for x in range(Nlanes)]
    for lane in laneIDs:
        loopfile.write('\t<inductionLoop id="{}" lane="{}" pos="{}" freq="{}" file="{}"/>\n'.format(loopID, lane, loc, freq, ofile))
        loopID += 1

for edge in endEdges:
    loc = -distanceFromFringe
    Nlanes = len(edge.getLanes())
    laneIDs = [edge.getID()+'_'+str(x) for x in range(Nlanes)]
    for lane in laneIDs:
        loopfile.write('\t<inductionLoop id="{}" lane="{}" pos="{}" freq="{}" file="{}"/>\n'.format(loopID, lane, loc, freq, ofile))
        loopID += 1

loopfile.write('</additional>\n')
loopfile.close()
