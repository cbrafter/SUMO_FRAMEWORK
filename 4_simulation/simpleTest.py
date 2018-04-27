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


class stopDict(defaultdict):
    def __missing__(self, key):
        self[key] = [0, 1]
        return self[key]

def getStops(stopStore, subKey):
    subResults = traci.edge.getContextSubscriptionResults(subKey)
    vtol = 1e-3
    if subResults not in [[], None, False, {}]:
        for vehID in subResults.keys():
            if tc.VAR_SPEED in subResults[vehID].keys():
                if stopStore[vehID][1] >= vtol and subResults[vehID][tc.VAR_SPEED] < vtol:
                    stopStore[vehID][0] += 1
                    stopStore[vehID][1] = subResults[vehID][tc.VAR_SPEED]
                else:
                    stopStore[vehID][1] = subResults[vehID][tc.VAR_SPEED]
    return stopStore


exectime = time.time()
#controller = HybridVAControl.HybridVAControl
#controller = HVAskip.HybridVAControl
#controller = actuatedControl.actuatedControl
#controller = VAskip.actuatedControl
controller = fixedTimeControl.fixedTimeControl
#controller = GPSControl.GPSControl
# Define road model directory
modelname = 'corridor'
modelBase  = modelname if 'selly' not in modelname else modelname.split('_')[0]
model = '../2_models/{}/'.format(modelBase)
# Generate new routes
stepSize = 0.1
CVP = 0.0
seed = 10

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
jd = readJunctionData.readJunctionData(model + modelBase + ".jcn.xml")
junctionsList = jd.getJunctionData()

# Add controller models to junctions
controllerList = []
minGreenTime = 10
maxGreenTime = 60
for junction in junctionsList:
    controllerList.append(controller(junction))

print('Junctions and controllers acquired')

# Step simulation while there are vehicles
vehIDs = []
juncIDs = traci.trafficlights.getIDList()
juncPos = [traci.junction.getPosition(juncID) for juncID in juncIDs]

# Step simulation while there are vehicles
i, flag = 1, True
'''
subKey = traci.edge.getIDList()[0]
traci.edge.subscribeContext(subKey, 
    tc.CMD_GET_VEHICLE_VARIABLE, 
    1000000, 
    varIDs=(tc.VAR_SPEED,))
# stopCounter = stopDict()
'''
while flag:
    # connector.runSimulationForSeconds(1)
    traci.simulationStep()
    for controller in controllerList:
        controller.process()
    # stopCounter = getStops(stopCounter, subKey)
    i += 1

    # reduce calls to traci to 1 per sec to impove performance
    flag = traci.simulation.getMinExpectedNumber() if not i%100 else True

'''
stopfilename = exportPath[4:]+'stops{:03d}_{:03d}.csv'.format(int(CVP*100), seed)
with open(stopfilename, 'w') as f:
    f.write('vehID,stops\n')
    vehIDs = map(int, stopCounter.keys())
    vehIDs.sort()
    vehIDs = map(str, vehIDs)
    for vehID in vehIDs:
        f.write('{},{}\n'.format(vehID, stopCounter[vehID][0]))
'''
connector.disconnect()
exectime = time.strftime("%H:%M:%S", time.gmtime(time.time() - exectime))
print('Simulations complete, exectime: {}, {}'.format(exectime, time.ctime()))
print('DONE')
