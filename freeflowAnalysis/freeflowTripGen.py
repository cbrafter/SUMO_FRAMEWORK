# -*- coding: utf-8 -*-
"""
@file    simpleTest.py
@author  Craig Rafter
@date    29/01/2016

"""
import os
import itertools
from glob import glob


types = ['car', 'bus', 'lgv', 'hgv', 'motorcycle']
vehicleTypeDef = """    <!--PASSENGER CAR-->
    <vType id="car" length="4.3" minGap="2.5"
        accel="2.6" decel="4.5" sigma="0.5" maxSpeed="50"
        color="240,228,66"/>
    <!--MOTORCYCLE-->
    <vType id="motorcycle" length="2.2" minGap="2.5"
        accel="5.0" decel="9.0" sigma="0.5" maxSpeed="55"
        color="36,255,36"/>
    <!--LGV-->
    <vType id="lgv" length="6.5" minGap="2.5"
        accel="2.0" decel="4.0" sigma="0.5" maxSpeed="44"
        color="86,180,233"/>
    <!--HGV-->
    <vType id="hgv" length="7.1" minGap="2.5"
        accel="1.3" decel="3.5" sigma="0.5" maxSpeed="36"
        color="0,158,115"/>
    <!--BUS-->
    <vType id="bus" length="12.0" minGap="2.5"
        accel="1.0" decel="3.5" sigma="0.5" maxSpeed="24"
        color="255,109,182"/>

"""
tab = 4*' '
endl = '\n'
validRouteFiles = glob('./FREEFLOW_TRIPS/valid_*.rou.xml')
vehicleStr = tab +\
             '<vehicle id="{}" type="{}" route="{}" depart="{}" ' +\
             'departLane="best" departSpeed="max"/>' +\
             endl
for routeFile in validRouteFiles:
    routes = []
    with open(routeFile, 'r') as f:
        for line in f.readlines():
            if '<route ' in line:
                routes.append(line)
    path, fname = os.path.split(routeFile)
    freeFlowFile = os.path.join(path, 'freeflow_' + fname.split('_')[1])

    vehicles = itertools.product(types, range(len(routes)))
    vehicleID = 0
    insertTime = 0
    delta = 350  # longest journey takes 342 seconds
    with open(freeFlowFile, 'w') as f:
        f.write('<routes>\n')
        f.write(vehicleTypeDef)
        for r in routes:
            f.write(tab+r.strip()+endl)
        f.write(endl)
        for vType, routeID in vehicles:
            f.write(vehicleStr.format(vehicleID, vType,
                                      routeID, insertTime))
            vehicleID += 1
            insertTime += delta
        f.write('</routes>\n')
