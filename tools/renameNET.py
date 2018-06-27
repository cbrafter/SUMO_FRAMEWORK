# -*- coding: utf-8 -*-
"""
A script that generates a validates list of OD pairs in the SUMO XML format.
Especially useful if importing from OSM and then editing manually to remove 
mixed OSM/SUMO nameing conventions.
- edges get renamed edge<INT>
- Traffic light junctions are renamed junc<INT>
- Node junctions are renamed node<INT>

Usage
-----
python renameNET.py model.net.xml

Output
------
REN_model.net.xml : XML file
    The input model with the renaming process applied. Input model is unchanged

author: Craig B. Rafter
mailto: c.b.rafter@soton.ac.uk
date: 01/09/2017
copyright: GNU GPL v3.0 - attibute me if used
"""
from __future__ import print_function
from __future__ import absolute_import
import os
import sys
import re

SUMO_HOME = '/usr/share/sumo'
sys.path.append(os.path.join(SUMO_HOME, 'tools'))
import sumolib

def isTrafficLight(node):
    return node.getType() == 'traffic_light'

# import net file
netfilename = sys.argv[1]
path, file = os.path.split(netfilename)
renamednet = path+'/REN_'+file
net = sumolib.net.readNet(netfilename)

# Remember special charaters in regex need to be escaped
# Get edges IDs
edgeIDs = [re.escape(edge.getID()) for edge in net.getEdges()]

# Get TL junction IDs
tlIDs = [re.escape(node.getID()) for node in net.getNodes() if isTrafficLight(node)]

# Get node junction IDs
nodeIDs = [re.escape(node.getID()) for node in net.getNodes() if not isTrafficLight(node)]

# Generate mappings for substitution
# Precompile the values to be substituted as they will be used repeatedly
# providing significant performance boost
edgeMaps = [[re.compile(x), 'edge'+str(i)] for i, x in enumerate(edgeIDs)]
tlMaps = [[re.compile(x), 'junc'+str(i)] for i, x in enumerate(tlIDs)]
nodeMaps = [[re.compile(x), 'node'+str(i)] for i, x in enumerate(nodeIDs)]
allMaps = edgeMaps + tlMaps + nodeMaps
# allMaps = [lambda x: regex.sub(subStr, x) for regex, subStr in allMaps]

# Renaming
# regex replace lines
with open(netfilename, 'r') as f:
    lines = f.readlines()
    for i in range(len(lines)):
        for regex, subStr in allMaps:
            # perform all regex substitutions on every line
            lines[i] = regex.sub(subStr, lines[i])

with open(renamednet, 'w') as f:
    f.writelines(lines)
