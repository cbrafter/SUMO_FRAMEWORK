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
copyright: GNU GPL v3.0 - attibute me if used
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
junctionInputLanes = []

# get traffic lights
for TL in net.getTrafficLights():
    # get connections
    for cnxn in TL.getConnections():
        junctionInputLanes.append(cnxn[0].getID())

# Get unique input lanes
junctionInputLanes = list(set(junctionInputLanes))

# write loops to file
loopfilename = 'loops.det.xml'
loopfile = open(loopfilename, 'w')
loopfile.write("""<?xml version="1.0"?>
<additional>
""")
loopID = 0
for lane in junctionInputLanes:
    for loc in sys.argv[2:]:
        loopfile.write('\t<inductionLoop id="{}" lane="{}" pos="{}" freq="300" file="loops.out"/>\n'.format(loopID, lane, loc))
        loopID += 1

loopfile.write('</additional>\n')
loopfile.close()
