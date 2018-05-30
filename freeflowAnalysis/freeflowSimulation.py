# -*- coding: utf-8 -*-
"""
@file    simpleTest.py
@author  Simon Box, Craig Rafter
@date    29/01/2016

test Miller's algorithm
"""
import sys, os
sys.path.insert(0, '../1_sumoAPI')
import sumoConnect
import readJunctionData
import traci
from freeflowConfigGen import sumoConfigGen
import re
import numpy as np
import traci.constants as tc
import time
from collections import defaultdict


exectime = time.time()
# Define road model directory
modelname = 'cross'
model = '../2_models/{}/'.format(modelname)
# Generate new routes
stepSize = 0.1
CVP = 0.0
seed = 5

# Edit the the output filenames in sumoConfig
configFile = model + modelname + ".sumocfg"
exportPath = '../../testing/results/'
if not os.path.exists(model+exportPath): # this is relative to cfg
    os.makedirs(model+exportPath)

simport = 8857
sumoConfigGen(modelname, configFile, exportPath,
              CVP=CVP, stepSize=stepSize,
              run=seed, port=simport, seed=seed)

# Connect to model
connector = sumoConnect.sumoConnect(model + modelname + ".sumocfg",
                                    gui=False, port=simport)
connector.launchSumoAndConnect()
print('Model connected')

# Set all lights green for free flow
juncIDs = traci.trafficlights.getIDList()
for tlsID in juncIDs:
    signal = traci.trafficlights.getRedYellowGreenState(tlsID)
    traci.trafficlights.setRedYellowGreenState(tlsID, 'G'*len(signal))

# Step simulation while there are vehicles
i, flag = 1, True
while flag:
    traci.simulationStep()
    i+=1
    if not i%200: 
        flag = traci.simulation.getMinExpectedNumber()
    else:
        flag = True
    # stopCounter = getStops(stopCounter, subKey)

connector.disconnect()
exectime = time.strftime("%H:%M:%S", time.gmtime(time.time() - exectime))
print('Simulations complete, exectime: {}, {}'.format(exectime, time.ctime()))
print('DONE')
