# -*- coding: utf-8 -*-
"""
A script that generates a validates list of OD pairs in the SUMO XML format.
NOTE: requires that the fringe edges be straight.

Usage
-----
python routeFind.py model.net.xml

Output
------
valid_routes.rou.xml : XML file
    All unique valid routes as ID'd routes

routes.rou.xml : XML file
    All valid routes as vehicle route trips so that you can test them on 
    a model using sumo/sumo-gui

author: Craig B. Rafter
mailto: c.b.rafter@soton.ac.uk
date: 01/09/2017
copyright: GNU GPL v3.0 - attibute me if used
"""
from __future__ import print_function
from __future__ import absolute_import
import os
import sys
import subprocess
import numpy as np
import xml.etree.ElementTree as ET

SUMO_HOME = '/usr/share/sumo'
sys.path.append(os.path.join(SUMO_HOME, 'tools'))
import sumolib

# Import duarouter for creating valid routes
DUAROUTER = sumolib.checkBinary('duarouter')

# import net file
netfilename = sys.argv[1]
net = sumolib.net.readNet(netfilename)

# find the fringe edges and see if it's a starting/ending edge
startEdges = []
endEdges = []
edgeShapes = {}
edgeIOpairs = {}

for edge in net.getEdges():
    if edge.is_fringe() and not len(edge.getIncoming()):
        strID = str(edge.getID())
        startEdges.append(strID)
        edgeShapes[strID] = edge.getShape()
    elif edge.is_fringe() and not len(edge.getOutgoing()):
        strID = str(edge.getID())
        endEdges.append(strID)
        edgeShapes[strID] = edge.getShape()
    else:
        continue

# Find Edge I/O pairs
ATOL = 10
for edge1 in startEdges:
    x1, y1, x2, y2 = [a for b in edgeShapes[edge1] for a in b]
    for edge2 in endEdges:
        if edge1 != edge2:
            x3, y3, x4, y4 = [a for b in edgeShapes[edge2] for a in b]
            if np.isclose(x2, x3, atol=ATOL) and np.isclose(y2, y3, atol=ATOL):
                edgeIOpairs[edge1] = edge2
            else:
                edgeIOpairs[edge1] = 'oneway'


# Generate the trips for the starting and ending edges
tripfilename = 'trips.trips.xml'
tripfile = open(tripfilename, 'w')
tripfile.write("""<?xml version="1.0"?>
<routes xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/routes_file.xsd">
""")
tripID = 0
for edge1 in startEdges:
    for edge2 in endEdges:
        if edge2 != edgeIOpairs[edge1]:
            tripfile.write('\t<trip id="{}" depart="{}" from="{}" to="{}"/>\n'.format(tripID, float(tripID), edge1, edge2))
            tripID += 1

tripfile.write('</routes>\n')
tripfile.close()

# Use DUAROUTER to generate and validate the routes
routefilename = 'routes.rou.xml'
routecmd = [DUAROUTER, '-n', netfilename, '-t', tripfilename, 
            '-o', routefilename, '--ignore-errors',
            '--begin', '0', '--end', str(tripID),
            '--no-step-log', '--no-warnings']

print("calling ", " ".join(routecmd))
subprocess.call(routecmd)


# Get the validated routes and write to new file
routeTree = ET.parse(routefilename)
routes = routeTree.getroot()
validRoutes = [r[0].items()[0][1] for r in routes]

routefile = open('valid_' + routefilename, 'w')

routefile.write("""<?xml version="1.0" encoding="UTF-8"?>
<routes xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/routes_file.xsd">
""")
for idx, route in enumerate(validRoutes):
    routefile.write('    <route id="{}" edges="{}"/>\n'.format(idx, route))

routefile.write('</routes>\n')
routefile.close()
print('Route generation complete!')
