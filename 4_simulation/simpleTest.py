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
modelname = 'twinT'
modelBase  = modelname if 'selly' not in modelname else modelname.split('_')[0]
model = '../2_models/{}/'.format(modelBase)
# Generate new routes
stepSize = 0.1
CVP = np.linspace(0, 1, 11)[8]
seed = 2

ctrl = str(controller).split('.')[1][:-2]
print('STARTING: {}, {}, Run: {:03d}, AVR: {:03d}%, Date: {}'
      .format(modelname, ctrl, seed, int(CVP*100), time.ctime()))

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
# juncPos = [traci.junction.getPosition(juncID) for juncID in juncIDs]

# Step simulation while there are vehicles
simTime, simActive = 0, True
timeLimit = 3*60*60  # 10 hours in seconds for time limit
subKey = sigTools.stopSubscription()
stopCounter = sigTools.stopDict()
timeDelta = int(1000*stepSize)
oneMinute = 60000  # one minute in simulation 60sec im msec
'''
subJunc = controllerList[0].junctionData.id
traci.junction.subscribeContext(subJunc, 
    tc.CMD_GET_VEHICLE_VARIABLE, 
    1000000, 
    varIDs=(tc.VAR_POSITION, tc.VAR_ANGLE, tc.VAR_SPEED,
            tc.VAR_TYPE, tc.VAR_WAITING_TIME))

# only subscribe to loop params if necessary
traci.junction.subscribeContext(subJunc, 
    tc.CMD_GET_INDUCTIONLOOP_VARIABLE, 
    1000000, 
    varIDs=(tc.LAST_STEP_TIME_SINCE_DETECTION,))
'''
while simActive:
    traci.simulationStep()
    # subResults = traci.junction.getContextSubscriptionResults(subJunc)
    for controller in controllerList:
        controller.process(time=simTime)
    stopCounter = sigTools.getStops(stopCounter, subKey)
    simTime += timeDelta
    # reduce calls to traci to 1 per simulation min to improve performance
    # flag will always be positive int while there are vehicles no need for else
    if not simTime % oneMinute: 
        simActive = traci.simulation.getMinExpectedNumber()
        # stop sim to free resources if taking longer than ~10 hours
        # i.e. the sim is gridlocked
        if timer.runtime() > timeLimit:
            connector.disconnect()
            raise RuntimeError("RuntimeError: GRIDLOCK")

stopfilename = './test_results/stops_R{:03d}_CVP{:03d}.csv'.format(seed, int(CVP*100))
sigTools.writeStops(stopCounter, stopfilename)

connector.disconnect()
timer.stop()
print('Simulations complete, exectime: {}, {}'.format(timer.strTime(), time.ctime()))
print('DONE')
