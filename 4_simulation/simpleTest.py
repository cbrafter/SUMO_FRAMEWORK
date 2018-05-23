# -*- coding: utf-8 -*-
"""
@file    simpleTest.py
@author  Simon Box, Craig Rafter
@date    29/01/2016

test Miller's algorithm
"""
import sys
import os
sys.path.insert(0, '../1_sumoAPI')
sys.path.insert(0, '../3_signalControllers')
import fixedTimeControl
import HybridVAControl
import actuatedControl
import VAskip
import HVAskip
import GPSControl
import sumoConnect
import readJunctionData
import traci
from sumoConfigGen import sumoConfigGen
import numpy as np
import traci.constants as tc
import time
from collections import defaultdict
import signalTools as sigTools


timer = sigTools.simTimer()
timer.start()
controller = HybridVAControl.HybridVAControl
#controller = actuatedControl.actuatedControl
controller = fixedTimeControl.fixedTimeControl
# Define road model directory
modelname = 'cross'
modelBase  = modelname if 'selly' not in modelname else modelname.split('_')[0]
model = '../2_models/{}/'.format(modelBase)
# Generate new routes
stepSize = 0.1
CVP = np.linspace(0, 1, 11)[8]
seed = 2

# Edit the the output filenames in sumoConfig
configFile = model + modelBase + ".sumocfg"
exportPath = '../../4_simulation/test_results/'
if not os.path.exists(model+exportPath): # this is relative to cfg
    os.makedirs(model+exportPath)

simport = 8857
sumoConfigGen(modelname, configFile, exportPath, 
              CVP=CVP, stepSize=stepSize, 
              run=seed, port=simport, seed=seed)

# Connect to model
connector = sumoConnect.sumoConnect(configFile, gui=False, port=simport)
connector.launchSumoAndConnect()
print('Model connected')

# Get junction data
jd = readJunctionData.readJunctionData(model + modelBase + ".jcn.xml")
junctionsList = jd.getJunctionData()

# Add controller models to junctions
controllerList = []
minGreenTime = 10
maxGreenTime = 60
for junction in junctionsList:
    if controller == HybridVAControl.HybridVAControl:
        print('YURT')
        controllerList.append(controller(junction, loopIO=True, model=modelBase))
    else:
        print('YIP')
        controllerList.append(controller(junction))

print('Junctions and controllers acquired')

# Step simulation while there are vehicles
vehIDs = []
juncIDs = traci.trafficlights.getIDList()
juncPos = [traci.junction.getPosition(juncID) for juncID in juncIDs]

# Step simulation while there are vehicles
i, flag = 0, True
timeLimit = 3*60*60  # 10 hours in seconds for time limit
subKey = sigTools.stopSubscription()
stopCounter = sigTools.stopDict()
oneMinute = 600  # one minute in simulation

while flag:
    traci.simulationStep()
    for controller in controllerList:
        controller.process()
    stopCounter = sigTools.getStops(stopCounter, subKey)
    i += 1

    # reduce calls to traci to 1 per simulation min to improve performance
    # flag will always be positive int while there are vehicles no need for else
    if not i%oneMinute: 
        flag = traci.simulation.getMinExpectedNumber()
        # stop sim to free resources if taking longer than ~10 hours
        # i.e. the sim is gridlocked
        if timer.runtime() > timeLimit:
            connector.disconnect()
            raise RuntimeError("RuntimeError: GRIDLOCK")

stopfilename = './test_results/stops{:03d}_{:03d}.csv'.format(int(CVP*100), seed)
sigTools.writeStops(stopCounter, stopfilename)

connector.disconnect()
timer.stop()
print('Simulations complete, exectime: {}, {}'.format(timer.strTime(), time.ctime()))
print('DONE')
