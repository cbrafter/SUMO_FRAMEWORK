# -*- coding: utf-8 -*-
import sys
import os
import shutil
import psutil
import subprocess
import time
import numpy as np
# from matplotlib import pyplot
from routeGen import routeGen
from sumoConfigGen import sumoConfigGen
from stripXML import stripXML
import multiprocessing as mp
from glob import glob
sys.path.insert(0, '../1_sumoAPI')
sys.path.insert(0, '../3_signalControllers')
import GPSControl
import fixedTimeControl
import actuatedControl
import HybridVAControl
import sumoConnect
import readJunctionData
print(sys.path)
import traci

print('Running the script! {} {}'.format(sys.argv[1], sys.argv[2]))
#os.mkdir('/hardmem/results/stuff/')
# with open('/hardmem/results/stuff/sampleT.txt', 'w') as f:
#     f.write('Hello World! {} {}'.format(sys.argv[1], sys.argv[2]))

# print(os.path.exists('/hardmem/results/stuff/'))
# print([psutil.cpu_count(), psutil.cpu_count(logical=False)])
def simulation(x):
    assert len(x) == 4
    runtime = time.time()
    # Define Simulation Params
    modelName, tlLogic, CAVratio, run = x
    procID = 1
    model = '../2_models/{}_{}/'.format(modelName, procID)
    simport = 8812 + procID
    stepSize = 0.1
    CVP = 0.0
    configFile = model + modelName + ".sumocfg"
    # Configure the Map of controllers to be run
    tlControlMap = {'fixedTime': fixedTimeControl.fixedTimeControl,
                    'VA': actuatedControl.actuatedControl,
                    'GPSVA': GPSControl.GPSControl,
                    'HVA': HybridVAControl.HybridVAControl}
    tlController = tlControlMap[tlLogic]
    print('Initial setup complete'); sys.stdout.flush()
    
    exportPath = '/hardmem/results/' + tlLogic + '/' + modelName + '/'
    print(exportPath + ' Exists: ' + str(os.path.exists(exportPath))); sys.stdout.flush()
    
    # Check if model copy for this process exists
    if not os.path.isdir(model):
        shutil.copytree('../2_models/{}/'.format(modelName), model)

    # this is relative to script not cfg file
    if not os.path.exists(exportPath):
        print('MADE PATH'); sys.stdout.flush()
        os.makedirs(exportPath)

    seed = 5

    # Edit the the output filenames in sumoConfig
    sumoConfigGen(modelName, configFile, exportPath, 
                  CVP=CVP, stepSize=stepSize, 
                  run=seed, port=simport, seed=seed)

    print('configuration complete'); sys.stdout.flush()
    # Connect to model
    connector = sumoConnect.sumoConnect(configFile, gui=False, port=simport)
    connector.launchSumoAndConnect()

    print('connection made'); sys.stdout.flush()
    # Get junction data
    jd = readJunctionData.readJunctionData(model + modelName + ".jcn.xml")
    junctionsList = jd.getJunctionData()

    # Add controller models to junctions
    controllerList = []
    for junction in junctionsList:
        controllerList.append(tlController(junction))

    print('Controllers set, running sim...'); sys.stdout.flush()
    # Step simulation while there are vehicles
    while traci.simulation.getMinExpectedNumber():
        # connector.runSimulationForSeconds(1)
        traci.simulationStep()
        for controller in controllerList:
            controller.process()

    # Disconnect from current configuration
    connector.disconnect()
    print('Sim complete'); sys.stdout.flush()
    runtime = time.gmtime(time.time() - runtime)
    print('DONE: {}, {}, Run: {:03d}, AVR: {:03d}%, Runtime: {}\n'
        .format(modelName, tlLogic, run, int(CAVratio*100), 
                time.strftime("%H:%M:%S", runtime)))
    return True

simulation(['simpleT', 'fixedTime', 0.1, 10])