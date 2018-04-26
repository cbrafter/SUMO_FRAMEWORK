# -*- coding: utf-8 -*-
import sys
import os
import shutil
import psutil
import subprocess
import time
import numpy as np
import multiprocessing as mp
import itertools
from collections import defaultdict
from sumoConfigGen import sumoConfigGen
from stripXML import stripXML
from glob import glob
sys.path.insert(0, '../1_sumoAPI')
import sumoConnect
import readJunctionData
sys.path.insert(0, '../3_signalControllers')
import GPSControl
import fixedTimeControl
import actuatedControl
import HybridVAControl
import HVAbias
import HVA1
import traci
import traci.constants as tc

# default dict that finds and remembers stops
# needs to be updated otherwise
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


def simulation(x):
    try:
        assert len(x) == 4
        runtime = time.time()
        # Define Simulation Params
        modelName, tlLogic, CVP, run = x
        modelBase  = modelName if 'selly' not in modelName else modelName.split('_')[0]
        procID = int(mp.current_process().name[-1])
        model = '../2_models/{}_{}/'.format(modelBase, procID)
        simport = 8812 + procID
        seed = int(run)
        stepSize = 0.1
        configFile = model + modelBase + ".sumocfg"

        # Configure the Map of controllers to be run
        tlControlMap = {'fixedTime': fixedTimeControl.fixedTimeControl,
                        'VA': actuatedControl.actuatedControl,
                        #'GPSVA': GPSControl.GPSControl,
                        'GPSVA': HybridVAControl.HybridVAControl,
                        'HVA': HybridVAControl.HybridVAControl,
                        'HVAslow': HybridVAControl.HybridVAControl,
                        'GPSVAslow': HybridVAControl.HybridVAControl}
        tlController = tlControlMap[tlLogic]

        exportPath = '/hardmem/results/' + tlLogic + '/' + modelName + '/'

        # Check if model copy for this process exists
        if not os.path.isdir(model):
            shutil.copytree('../2_models/{}/'.format(modelBase), model)

        # this is relative to script not cfg file
        if not os.path.exists(exportPath):
            os.makedirs(exportPath)

        # Edit the the output filenames in sumoConfig
        sumoConfigGen(modelName, configFile, exportPath, 
              CVP=CVP, stepSize=stepSize, 
              run=seed, port=simport, seed=seed)

        # Connect to model
        connector = sumoConnect.sumoConnect(configFile, gui=False, port=simport)
        connector.launchSumoAndConnect()

        # Get junction data
        jd = readJunctionData.readJunctionData(model + modelBase + ".jcn.xml")
        junctionsList = jd.getJunctionData()

        # Add controller models to junctions
        controllerList = []
        # Turn loops off if CAV ratio > 50%
        # loopIO = True if CAVratio < 0.5 else False
        for junction in junctionsList:
            if 'HVA' in tlLogic: 
                if 'slow' in tlLogic:
                    controllerList.append(tlController(junction, 
                                                       loopIO=True,
                                                       CAMoverride=1))
                else:
                    controllerList.append(tlController(junction, loopIO=True))
            # GPSVA is just HVA with the loops turned off
            elif 'GPSVA' in tlLogic:
                if 'slow' in tlLogic:
                    controllerList.append(tlController(junction, 
                                                       loopIO=False,
                                                       CAMoverride=1))
                else:
                    controllerList.append(tlController(junction, loopIO=False))
            else:
                controllerList.append(tlController(junction))

        # Step simulation while there are vehicles
        i, flag = 1, True
        timeLimit = 10*60*60  # 10 hours in seconds for time limit
        # subKey = traci.edge.getIDList()[0]
        # traci.edge.subscribeContext(subKey, 
        #     tc.CMD_GET_VEHICLE_VARIABLE, 
        #     1000000, 
        #     varIDs=(tc.VAR_SPEED,))
        # stopCounter = stopDict()

        # Flush print buffer
        sys.stdout.flush()

        while flag:
            # connector.runSimulationForSeconds(1)
            traci.simulationStep()
            for controller in controllerList:
                controller.process()
            # stopCounter = getStops(stopCounter, subKey)
            i += 1
            # reduce calls to traci to 1 per sec to impove performance
            if not i%200: 
                flag = traci.simulation.getMinExpectedNumber()
                # stop sim to free resources if taking longer than ~10 hours
                # i.e. the sim is gridlocked
                if time.time()-runtime > timeLimit:
                    connector.disconnect()
                    raise RuntimeError("RuntimeError: GRIDLOCK")
            else: 
                flag = True

        # Disconnect from current configuration
        connector.disconnect()

        # save stops file
        '''
        stopfilename = exportPath+'stops{:03d}_{:03d}.csv'.format(int(CAVratio*100), seed)
        with open(stopfilename, 'w') as f:
            f.write('vehID,stops\n')
            #vehIDs = map(int, stopCounter.keys())
            #vehIDs.sort()
            #vehIDs = map(str, vehIDs)
            for vehID in stopCounter.keys():
                f.write('{},{}\n'.format(vehID, stopCounter[vehID][0]))
        '''

        runtime = time.gmtime(time.time() - runtime)
        runtime = time.strftime("%H:%M:%S", runtime)
        print('DONE: {}, {}, Run: {:03d}, AVR: {:03d}%, Runtime: {}, Date: {}'
            .format(modelName, tlLogic, run, int(CVP*100), 
                    runtime , time.ctime()))
        sys.stdout.flush()
        return True
    except Exception as e:
        # Print if an experiment fails and provide repr of params to repeat run
        runtime = time.gmtime(time.time() - runtime)
        runtime = time.strftime("%H:%M:%S", runtime)
        print('***FAILURE '+runtime+', '+time.ctime()+'*** '+repr(x))
        print(str(e))
        sys.stdout.flush()
        return False

################################################################################
# MAIN SIMULATION DEFINITION
################################################################################
exectime = time.time()
models = ['cross', 'simpleT', 'twinT', 'corridor',
          'sellyOak_avg', 'sellyOak_lo', 'sellyOak_hi']
tlControllers = ['fixedTime', 'VA', 'HVA', 'GPSVA', 'HVAslow', 'GPSVAslow']
CAVratios = np.linspace(0, 1, 11)

if len(sys.argv) >= 3:
    runArgs = sys.argv[1:3]
    runArgs = [int(arg) for arg in runArgs]
    runArgs.sort()
    runStart, runEnd = runArgs
else:
    runStart, runEnd = [1, 11]

runIDs = np.arange(runStart, runEnd)

configs = []
# Generate all simulation configs for fixed time and VA
configs += list(itertools.product(models[::-1],
                                  tlControllers[:2],
                                  [0.],
                                  runIDs))
# Generate runs for CAV dependent controllers
configs += list(itertools.product(models[::-1],
                                  tlControllers[2:],
                                  CAVratios[::-1],
                                  runIDs))
# Test configurations
configs = list(itertools.product(models[-3:], tlControllers[:1], CAVratios[:1], runIDs))


print('# simulations: '+str(len(configs)))

# define number of processors to use (avg of logical and physical cores)
nproc = np.mean([psutil.cpu_count(), 
                 psutil.cpu_count(logical=False)], 
                 dtype=int)

nproc = 6
print('Starting simulation on {} cores'.format(nproc)+' '+time.ctime())  
# define work pool
workpool = mp.Pool(processes=nproc)
# Run simualtions in parallel
result = workpool.map(simulation, configs, chunksize=1)
# remove spawned model copies
for rmdir in glob('../2_models/*_*'):
    if os.path.isdir(rmdir):
        shutil.rmtree(rmdir)

# Inform of failed expermiments
if all(result):
    exectime = time.strftime("%H:%M:%S", time.gmtime(time.time() - exectime))
    print('Simulations complete, no errors, exectime: {}'.format(exectime))
else:
    print('Failed Experiment Runs:')
    for i, j in zip(configs, result):
        if not j:
            print(i)
