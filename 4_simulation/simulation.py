# -*- coding: utf-8 -*-
import sys
import os
import shutil
import time
import multiprocessing as mp
from sumoConfigGen import sumoConfigGen
sys.path.insert(0, '../1_sumoAPI')
import sumoConnect
import readJunctionData
sys.path.insert(0, '../3_signalControllers')
import fixedTimeControl
import actuatedControl
import HybridVAControl
import traci
import signalTools as sigTools


def simulation(x):
    try:
        assert len(x) == 4
        timer = sigTools.simTimer()
        timer.start()
        # Define Simulation Params
        modelName, tlLogic, CVP, run = x
        modelBase  = modelName if 'selly' not in modelName else modelName.split('_')[0]
        procID = int(mp.current_process().name[-1])
        model = '../2_models/{}_{}/'.format(modelBase, procID)
        simport = 8812 + procID
        seed = int(run)
        stepSize = 0.1
        configFile = model + modelBase + ".sumocfg"

        print('STARTING: {}, {}, Run: {:03d}, AVR: {:03d}%, Date: {}'
              .format(modelName, tlLogic, run, int(CVP*100), time.ctime()))
        sys.stdout.flush()

        # Configure the Map of controllers to be run
        tlControlMap = {'fixedTime': fixedTimeControl.fixedTimeControl,
                        'VA': actuatedControl.actuatedControl,
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

        # Edit the the output filenames in sumoConfig
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
            if tlLogic in ['HVA', 'GPSVA']: 
                CAMmod = 1 if 'slow' in tlLogic else False
                loopCtrl = True if 'HVA' in tlLogic else False
                controllerList.append(tlController(junction, 
                                                   loopIO=loopCtrl,
                                                   CAMoverride=CAMmod,
                                                   model=modelBase))
            else:
                controllerList.append(tlController(junction))

        # Step simulation while there are vehicles
        i, flag = 0, True
        timeLimit = 10*60*60  # 10 hours in seconds for time limit
        subKey = traci.edge.getIDList()[0]
        subKey = sigTools.stopSubscription()
        stopCounter = sigTools.stopDict()
        oneMinute = 600
        # Flush print buffer
        sys.stdout.flush()

        while flag:
            traci.simulationStep()
            for controller in controllerList:
                controller.process()
            stopCounter = sigTools.getStops(stopCounter, subKey)
            i += 1
            # reduce calls to traci to 1 per sim min to improve performance
            if not i % oneMinute: 
                flag = traci.simulation.getMinExpectedNumber()
                # stop sim to free resources if taking longer than ~10 hours
                # i.e. the sim is gridlocked
                if timer.runtime() > timeLimit:
                    connector.disconnect()
                    raise RuntimeError("RuntimeError: GRIDLOCK")

        # Disconnect from current configuration
        connector.disconnect()

        # save stops file
        stopfilename = exportPath+'stops{:03d}_{:03d}.csv'.format(int(CVP*100), seed)
        sigTools.writeStops(stopCounter, stopfilename)

        timer.stop()
        print('DONE: {}, {}, Run: {:03d}, AVR: {:03d}%, Runtime: {}, Date: {}'
              .format(modelName, tlLogic, run, int(CVP*100),
                      timer.strTime(), time.ctime()))
        sys.stdout.flush()
        return True
    except Exception as e:
        # Print if an experiment fails and provide repr of params to repeat run
        timer.stop()
        print('***FAILURE '+timer.strTime()+', '+time.ctime()+'*** '+repr(x))
        print(str(e))
        sys.stdout.flush()
        return False
    finally:
        sys.stdout.flush()
