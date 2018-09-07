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
import TRANSYT
import HybridVAControl
import actuatedControl
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
#controller = fixedTimeControl.fixedTimeControl
#controller = TRANSYT.TRANSYT
# Define road model directory
modelname = 'sellyOak_hi'
modelBase = modelname.split('_')[0]
model = '../2_models/{}/'.format(modelBase)
# Generate new routes
stepSize = 0.1
CVP = np.linspace(0, 1, 11)[5]
#CVP = 0.6000000000000001
seed = 7

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
connector = sumoConnect.sumoConnect(configFile, gui=True, port=simport)
connector.launchSumoAndConnect()
print('Model connected')

# Get junction data
if 'selly' in model:
    jd = readJunctionData.readJunctionData(model + modelBase + ".t15.xml")
else:
    jd = readJunctionData.readJunctionData(model + modelBase + ".jcn.xml")

junctionData = jd.getJunctionData()

# Add controller models to junctions
controllerList = []
minGreenTime = 10
maxGreenTime = 60
for junction in junctionData:
    if controller == HybridVAControl.HybridVAControl:
        CAMmod = False
        loopCtrl = False
        noise = False
        PER = 0.0
        controllerList.append(controller(junction, 
                                         loopIO=loopCtrl,
                                         CAMoverride=CAMmod,
                                         model=modelBase,
                                         PER=PER, noise=noise))
    elif controller == TRANSYT.TRANSYT:
        controllerList.append(controller(junction))
    else:
        controllerList.append(controller(junction))

print('Junctions and controllers acquired')

# Step simulation while there are vehicles
vehIDs = []
juncIDs = traci.trafficlights.getIDList()
# juncPos = [traci.junction.getPosition(juncID) for juncID in juncIDs]

# Step simulation while there are vehicles
simTime, simActive = 0, True
# limit and extend are per 2.5 minute in test
timeLimit = 2.5*60  # 1 hours in seconds for time limit
limitExtend = 2.5*60 # check again in 20 mins if things seem ok
stopCounter = sigTools.StopCounter()
stopfilename = './test_results/stops_R{:03d}_CVP{:03d}.csv'.format(seed, int(CVP*100))
timeDelta = int(1000*stepSize)
oneMinute = 60*1000  # one minute in simulation 60sec im msec
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
    stopCounter.getStops()
    simTime += timeDelta
    # reduce calls to traci to 1 per simulation min to improve performance
    # flag will always be positive int while there are vehicles no need for else
    if not simTime % oneMinute: 
        simActive = traci.simulation.getMinExpectedNumber()
        # stop sim to free resources if taking longer than ~10 hours
        # i.e. the sim is gridlocked
        if timer.runtime() > timeLimit:
            stopCounter.writeStops(stopfilename)
            if sigTools.isSimGridlocked(modelBase, simTime):
                connector.disconnect()
                raise RuntimeError("RuntimeError: GRIDLOCK")
            else:
                print('EXTENDING')
                timeLimit += limitExtend

stopCounter.writeStops(stopfilename)
connector.disconnect()
timer.stop()
print('Simulations complete, exectime: {}, {}'.format(timer.strTime(), time.ctime()))
print('DONE')
