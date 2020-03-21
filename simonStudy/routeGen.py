#!/usr/bin/env python
"""
@file    routeGen.py
@author  Simon Box, Craig Rafter
@date    29/01/2016

Code to generate a routes file for the "simpleT" SUMO model.

"""
import random


def randCF(AVratio):
    ''' Assign random car following model based on AVratio
    '''
    return 'Human' if random.uniform(0, 1) >= AVratio else 'ITSCV'


def routeStr(vehNr, CFmodel, heading, Tdepart):
    ''' Generate XML route definition
    '''
    vID = 'vehicle id="%i" ' % (vehNr)
    vtype = 'type="type%s" ' % (CFmodel)
    route = 'route="%s" ' % (heading)
    depart = 'depart="%i" ' % (Tdepart)
    return '    <' + vID + vtype + route + depart + ' departLane="best" departSpeed="max"/>'


def routeGen(N, AVratio=0, AVtau=0.1, routeFile='./simpleT.rou.xml', seed=None): 
    assert 0.0 <= AVratio <= 1.0, "Error: AVratio not between 0,1"
    assert '.rou.xml' == routeFile[-8:], "Error: Wrong route file extension"

    random.seed(seed)

    # Open routefile for writing
    routes = open(routeFile, "w")
    # Insert route file header
    print >> routes, """<routes>
    <vType id="typeHuman" accel="2.6" decel="4.5" sigma="0.5" length="5" minGap="2.5" maxSpeed="31" departLane="best" departSpeed="max" guiShape="passenger" color="1,1,0">
    </vType>

    <vType id="typeITSCV" accel="2.6" decel="4.5" sigma="0.5" length="5" minGap="2.5" maxSpeed="31" departLane="best" departSpeed="max" guiShape="passenger" color="1,0,0">
        <carFollowing-Krauss tau="1.0"/>
    </vType>""".format(AVtau=AVtau)


    if ('plainRoad' in routeFile):
        print >> routes, """
    <route id="eastWest" edges="4:3 3:2 2:1 1:0" />
    <route id="westEast" edges="0:1 1:2 2:3 3:4" />
    """
        # Probabilities of car on trajectory
        routeList = [
            ['eastWest', 1.0/2.0], 
            ['westEast', 1.0/2.0]
        ]


    if ('simpleT' in routeFile):
        print >> routes, """
    <route id="eastSouth" edges="2:0 0:1 1:5 5:6" />
    <route id="eastWest" edges="2:0 0:1 1:3 3:7" />
    <route id="westSouth" edges="7:3 3:1 1:5 5:6" />
    <route id="westEast" edges="7:3 3:1 1:0 0:2" />
    <route id="southEast" edges="6:5 5:1 1:0 0:2" />
    <route id="southWest" edges="6:5 5:1 1:3 3:7" />
    """
        # Probabilities of car on trajectory
        prob = 0.475
        scaling = 0.2
        routeList = [
            ['eastSouth', prob*scaling], 
            ['eastWest', prob], 
            ['westSouth', prob*scaling], 
            ['westEast', prob], 
            ['southEast', prob*scaling*0.7], 
            ['southWest', prob*scaling*0.7]
        ]

    elif ('twinT' in routeFile):
        print >> routes, """
    <route id="8to6" edges="8:2 2:0 0:1 1:5 5:6" />
    <route id="8to7" edges="8:2 2:0 0:1 1:3 3:7" />
    <route id="8to10" edges="8:2 2:0 0:9 9:10" />
    <route id="7to6" edges="7:3 3:1 1:5 5:6" />
    <route id="7to8" edges="7:3 3:1 1:0 0:2 2:8" />
    <route id="7to10" edges="7:3 3:1 1:0 0:9 9:10" />
    <route id="6to8" edges="6:5 5:1 1:0 0:2 2:8" />
    <route id="6to7" edges="6:5 5:1 1:3 3:7" />
    <route id="6to10" edges="6:5 5:1 1:0 0:9 9:10" />
    <route id="10to6" edges="10:9 9:0 0:1 1:5 5:6" />
    <route id="10to7" edges="10:9 9:0 0:1 1:3 3:7" />
    <route id="10to8" edges="10:9 9:0 0:2 2:8" />
    """
        prob = 0.2
        scaling = 0.25
        routeList = [
            ["8to6", prob*scaling],
            ["8to7", prob],
            ["8to10", prob*scaling],
            ["7to6", prob*scaling],
            ["7to8", prob],
            ["7to10", prob],
            ["6to8", prob*scaling],
            ["6to7", prob*scaling],
            ["6to10", prob*scaling],
            ["10to6", prob*scaling],
            ["10to7", prob*scaling],
            ["10to8", prob*scaling]
        ]

    elif ('corridor' in routeFile):
        print >> routes, """
    <route edges="6:4 4:0 0:10 10:11 " id="6:4TO10:11"/>
    <route edges="6:4 4:0 0:1 1:2 2:3 3:16 16:17 " id="6:4TO16:17"/>
    <route edges="6:4 4:0 0:1 1:2 2:3 3:5 5:7 " id="6:4TO5:7"/>
    <route edges="6:4 4:0 0:1 1:2 2:14 14:15 " id="6:4TO14:15"/>
    <route edges="6:4 4:0 0:8 8:9 " id="6:4TO8:9"/>
    <route edges="6:4 4:0 0:1 1:2 2:3 3:18 18:19 " id="6:4TO18:19"/>
    <route edges="6:4 4:0 0:1 1:12 12:13 " id="6:4TO12:13"/>
    <route edges="9:8 8:0 0:4 4:6 " id="9:8TO4:6"/>
    <route edges="9:8 8:0 0:1 1:2 2:3 3:16 16:17 " id="9:8TO16:17"/>
    <route edges="9:8 8:0 0:1 1:2 2:3 3:5 5:7 " id="9:8TO5:7"/>
    <route edges="9:8 8:0 0:1 1:2 2:14 14:15 " id="9:8TO14:15"/>
    <route edges="9:8 8:0 0:10 10:11 " id="9:8TO10:11"/>
    <route edges="9:8 8:0 0:1 1:2 2:3 3:18 18:19 " id="9:8TO18:19"/>
    <route edges="9:8 8:0 0:1 1:12 12:13 " id="9:8TO12:13"/>
    <route edges="11:10 10:0 0:4 4:6 " id="11:10TO4:6"/>
    <route edges="11:10 10:0 0:1 1:2 2:3 3:16 16:17 " id="11:10TO16:17"/>
    <route edges="11:10 10:0 0:1 1:2 2:3 3:5 5:7 " id="11:10TO5:7"/>
    <route edges="11:10 10:0 0:1 1:2 2:14 14:15 " id="11:10TO14:15"/>
    <route edges="11:10 10:0 0:8 8:9 " id="11:10TO8:9"/>
    <route edges="11:10 10:0 0:1 1:2 2:3 3:18 18:19 " id="11:10TO18:19"/>
    <route edges="11:10 10:0 0:1 1:12 12:13 " id="11:10TO12:13"/>
    <route edges="13:12 12:1 1:0 0:10 10:11 " id="13:12TO10:11"/>
    <route edges="13:12 12:1 1:2 2:14 14:15 " id="13:12TO14:15"/>
    <route edges="13:12 12:1 1:0 0:8 8:9 " id="13:12TO8:9"/>
    <route edges="13:12 12:1 1:2 2:3 3:16 16:17 " id="13:12TO16:17"/>
    <route edges="13:12 12:1 1:0 0:4 4:6 " id="13:12TO4:6"/>
    <route edges="13:12 12:1 1:2 2:3 3:5 5:7 " id="13:12TO5:7"/>
    <route edges="13:12 12:1 1:2 2:3 3:18 18:19 " id="13:12TO18:19"/>
    <route edges="15:14 14:2 2:1 1:12 12:13 " id="15:14TO12:13"/>
    <route edges="15:14 14:2 2:3 3:18 18:19 " id="15:14TO18:19"/>
    <route edges="15:14 14:2 2:3 3:16 16:17 " id="15:14TO16:17"/>
    <route edges="15:14 14:2 2:3 3:5 5:7 " id="15:14TO5:7"/>
    <route edges="15:14 14:2 2:1 1:0 0:8 8:9 " id="15:14TO8:9"/>
    <route edges="15:14 14:2 2:1 1:0 0:10 10:11 " id="15:14TO10:11"/>
    <route edges="15:14 14:2 2:1 1:0 0:4 4:6 " id="15:14TO4:6"/>
    <route edges="17:16 16:3 3:2 2:1 1:0 0:8 8:9 " id="17:16TO8:9"/>
    <route edges="17:16 16:3 3:5 5:7 " id="17:16TO5:7"/>
    <route edges="17:16 16:3 3:2 2:1 1:0 0:10 10:11 " id="17:16TO10:11"/>
    <route edges="17:16 16:3 3:2 2:1 1:0 0:4 4:6 " id="17:16TO4:6"/>
    <route edges="17:16 16:3 3:18 18:19 " id="17:16TO18:19"/>
    <route edges="17:16 16:3 3:2 2:1 1:12 12:13 " id="17:16TO12:13"/>
    <route edges="17:16 16:3 3:2 2:14 14:15 " id="17:16TO14:15"/>
    <route edges="19:18 18:3 3:2 2:1 1:0 0:8 8:9 " id="19:18TO8:9"/>
    <route edges="19:18 18:3 3:5 5:7 " id="19:18TO5:7"/>
    <route edges="19:18 18:3 3:2 2:1 1:0 0:10 10:11 " id="19:18TO10:11"/>
    <route edges="19:18 18:3 3:2 2:1 1:0 0:4 4:6 " id="19:18TO4:6"/>
    <route edges="19:18 18:3 3:16 16:17 " id="19:18TO16:17"/>
    <route edges="19:18 18:3 3:2 2:1 1:12 12:13 " id="19:18TO12:13"/>
    <route edges="19:18 18:3 3:2 2:14 14:15 " id="19:18TO14:15"/>
    <route edges="7:5 5:3 3:18 18:19 " id="7:5TO18:19"/>
    <route edges="7:5 5:3 3:2 2:1 1:0 0:8 8:9 " id="7:5TO8:9"/>
    <route edges="7:5 5:3 3:2 2:1 1:0 0:4 4:6 " id="7:5TO4:6"/>
    <route edges="7:5 5:3 3:2 2:1 1:12 12:13 " id="7:5TO12:13"/>
    <route edges="7:5 5:3 3:16 16:17 " id="7:5TO16:17"/>
    <route edges="7:5 5:3 3:2 2:1 1:0 0:10 10:11 " id="7:5TO10:11"/>
    <route edges="7:5 5:3 3:2 2:14 14:15 " id="7:5TO14:15"/>
    """

        prob = 0.039
        routeList = [
            ["6:4TO10:11", prob],
            ["6:4TO16:17", prob],
            ["6:4TO5:7", prob],
            ["6:4TO14:15", prob],
            ["6:4TO8:9", prob],
            ["6:4TO18:19", prob],
            ["6:4TO12:13", prob],
            ["9:8TO4:6", prob/3],
            ["9:8TO16:17", prob/3],
            ["9:8TO5:7", prob/3],
            ["9:8TO14:15", prob/3],
            ["9:8TO10:11", prob/3],
            ["9:8TO18:19", prob/3],
            ["9:8TO12:13", prob/3],
            ["11:10TO4:6", prob/3],
            ["11:10TO16:17", prob/3],
            ["11:10TO5:7", prob/3],
            ["11:10TO14:15", prob/3],
            ["11:10TO8:9", prob/3],
            ["11:10TO18:19", prob/3],
            ["11:10TO12:13", prob/3],
            ["13:12TO10:11", prob/3],
            ["13:12TO14:15", prob/3],
            ["13:12TO8:9", prob/3],
            ["13:12TO16:17", prob/3],
            ["13:12TO4:6", prob/3],
            ["13:12TO5:7", prob/3],
            ["13:12TO18:19", prob/3],
            ["15:14TO12:13", prob/3],
            ["15:14TO18:19", prob/3],
            ["15:14TO16:17", prob/3],
            ["15:14TO5:7", prob/3],
            ["15:14TO8:9", prob/3],
            ["15:14TO10:11", prob/3],
            ["15:14TO4:6", prob/3],
            ["17:16TO8:9", prob/3],
            ["17:16TO5:7", prob/3],
            ["17:16TO10:11", prob/3],
            ["17:16TO4:6", prob/3],
            ["17:16TO18:19", prob/3],
            ["17:16TO12:13", prob/3],
            ["17:16TO14:15", prob/3],
            ["19:18TO8:9", prob/3],
            ["19:18TO5:7", prob/3],
            ["19:18TO10:11", prob/3],
            ["19:18TO4:6", prob/3],
            ["19:18TO16:17", prob/3],
            ["19:18TO12:13", prob/3],
            ["19:18TO14:15", prob/3],
            ["7:5TO18:19", prob],
            ["7:5TO8:9", prob],
            ["7:5TO4:6", prob],
            ["7:5TO12:13", prob],
            ["7:5TO16:17", prob],
            ["7:5TO10:11", prob],
            ["7:5TO14:15", prob]
        ]

    elif ('manhattan' in routeFile):
        print >> routes, """
    <route id="0" edges="a1:b1 b1:b2 b2:a2"/>
    <route id="1" edges="a1:b1 b1:b2 b2:b3 b3:b4"/>
    <route id="2" edges="a1:b1 b1:c1 c1:c0"/>
    <route id="3" edges="a1:b1 b1:c1 c1:d1 d1:e1"/>
    <route id="4" edges="a1:b1 b1:c1 c1:d1 d1:d2 d2:d3 d3:d4"/>
    <route id="5" edges="a1:b1 b1:c1 c1:d1 d1:d2 d2:d3 d3:e3"/>
    <route id="6" edges="a3:b3 b3:c3 c3:c2 c2:b2 b2:a2"/>
    <route id="7" edges="a3:b3 b3:b4"/>
    <route id="8" edges="a3:b3 b3:c3 c3:c2 c2:c1 c1:c0"/>
    <route id="9" edges="a3:b3 b3:c3 c3:c2 c2:c1 c1:d1 d1:e1"/>
    <route id="10" edges="a3:b3 b3:c3 c3:d3 d3:d4"/>
    <route id="11" edges="a3:b3 b3:c3 c3:d3 d3:e3"/>
    <route id="12" edges="b0:b1 b1:b2 b2:a2"/>
    <route id="13" edges="b0:b1 b1:b2 b2:b3 b3:b4"/>
    <route id="14" edges="b0:b1 b1:c1 c1:c0"/>
    <route id="15" edges="b0:b1 b1:c1 c1:d1 d1:e1"/>
    <route id="16" edges="b0:b1 b1:c1 c1:d1 d1:d2 d2:d3 d3:d4"/>
    <route id="17" edges="b0:b1 b1:c1 c1:d1 d1:d2 d2:d3 d3:e3"/>
    <route id="18" edges="c4:c3 c3:c2 c2:b2 b2:a2"/>
    <route id="19" edges="c4:c3 c3:c2 c2:b2 b2:b3 b3:b4"/>
    <route id="20" edges="c4:c3 c3:c2 c2:c1 c1:c0"/>
    <route id="21" edges="c4:c3 c3:c2 c2:c1 c1:d1 d1:e1"/>
    <route id="22" edges="c4:c3 c3:d3 d3:d4"/>
    <route id="23" edges="c4:c3 c3:d3 d3:e3"/>
    <route id="24" edges="d0:d1 d1:d2 d2:c2 c2:b2 b2:a2"/>
    <route id="25" edges="d0:d1 d1:d2 d2:c2 c2:b2 b2:b3 b3:b4"/>
    <route id="26" edges="d0:d1 d1:d2 d2:c2 c2:c1 c1:c0"/>
    <route id="27" edges="d0:d1 d1:e1"/>
    <route id="28" edges="d0:d1 d1:d2 d2:d3 d3:d4"/>
    <route id="29" edges="d0:d1 d1:d2 d2:d3 d3:e3"/>
    <route id="30" edges="e2:d2 d2:c2 c2:b2 b2:a2"/>
    <route id="31" edges="e2:d2 d2:c2 c2:b2 b2:b3 b3:b4"/>
    <route id="32" edges="e2:d2 d2:c2 c2:c1 c1:c0"/>
    <route id="33" edges="e2:d2 d2:c2 c2:c1 c1:d1 d1:e1"/>
    <route id="34" edges="e2:d2 d2:d3 d3:d4"/>
    <route id="35" edges="e2:d2 d2:d3 d3:e3"/>
    """
    # Probabilities of car on trajectory
        prob = 1
        scaling = 0.024
        routeList = [["0", prob*scaling],
                     ["1", prob*scaling],
                     ["2", prob*scaling],
                     ["3", prob],
                     ["4", prob*scaling],
                     ["5", prob*scaling],
                     ["6", prob*0],
                     ["7", prob*scaling],
                     ["8", prob*scaling],
                     ["9", prob*scaling],
                     ["10", prob*scaling],
                     ["11", prob],
                     ["12", prob*scaling],
                     ["13", prob*scaling],
                     ["14", prob*scaling],
                     ["15", prob*scaling],
                     ["16", prob*scaling],
                     ["17", prob*scaling],
                     ["18", prob*scaling],
                     ["19", prob*0],
                     ["20", prob*scaling],
                     ["21", prob*scaling],
                     ["22", prob*scaling],
                     ["23", prob*scaling],
                     ["24", prob*scaling],
                     ["25", prob*scaling],
                     ["26", prob*0],
                     ["27", prob*scaling],
                     ["28", prob*scaling],
                     ["29", prob*scaling],
                     ["30", prob],
                     ["31", prob*scaling],
                     ["32", prob*scaling],
                     ["33", prob*0],
                     ["34", prob*scaling],
                     ["35", prob*scaling]                     
        ]

    lastVeh = 0
    vehNr = 0
    for i in range(N):
        for routeInfo in routeList:
            if random.uniform(0, 1) < routeInfo[1]:
                print >> routes, routeStr(vehNr, randCF(AVratio), routeInfo[0], i)
                vehNr += 1
                lastVeh = i

    print >> routes, "</routes>"
    routes.close()
    return vehNr, lastVeh
