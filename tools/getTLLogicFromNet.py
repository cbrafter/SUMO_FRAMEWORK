# -*- coding: utf-8 -*-
"""
A script that extracts the TL logic from the net for use with SUMO API

Usage
-----
python getTLLogicFromNet.py model.net.xml

Output
------
junctions.jcn.xml : XML file
    Contins the junction information in SUMO API style

author: Craig B. Rafter
mailto: c.b.rafter@soton.ac.uk
date: 01/09/2017
copyright: GNU GPL v3.0 - attibute me if used
"""

from __future__ import print_function
from __future__ import absolute_import
import os
import sys
import xml.etree.ElementTree as ET

SUMO_HOME = '/usr/share/sumo'
sys.path.append(os.path.join(SUMO_HOME, 'tools'))

# import net file
netfilename = sys.argv[1]
path, file = os.path.split(netfilename)
jcnfile = path+'/'+file.split('.')[0]+'.jcn.xml'
netTree = ET.parse(netfilename)
net = netTree.getroot()

# get traffic lights
juncs = [x for x in list(net) if x.tag == 'tlLogic']

# write junctions to file
f = open(jcnfile, 'w')
f.write('<junctions>\n')
# Get each junction
for junc in juncs:
    ID = junc.attrib['id']
    offset = junc.attrib['offset']
    f.write('\t<junction id="{}" offset="{}">\n'.format(ID, offset))
    PID = 0  # phase ID
    # write junctions stage information
    for phase in junc:
        period = phase.attrib['duration']
        ctrlStr = phase.attrib['state']
        f.write('\t\t<stage id="{}" period="{}" controlString="{}"/>\n'.format(PID, period, ctrlStr))
        PID += 1
    f.write('\t</junction>\n')

f.write('</junctions>\n')
f.close()
