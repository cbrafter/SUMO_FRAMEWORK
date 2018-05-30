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

        print('STARTING: {}, {}, Run: {:03d}, CVP: {:03d}%, Date: {}'
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
            time.sleep(0.5)  # sleep to make sure files copied

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
        simTime, simActive = 0, True
        timeLimit = 11*60*60  # 10 hours in seconds for time limit
        subKey = sigTools.stopSubscription()
        stopCounter = sigTools.stopDict()
        timeDelta = int(1000*stepSize)
        oneMinute = 60000  # one minute in simulation 60sec im msec

        # Flush print buffer
        sys.stdout.flush()

        while simActive:
            traci.simulationStep()
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
                    raise RuntimeError("RuntimeError: TIMEOUT/GRIDLOCK")

        # Disconnect from current configuration
        connector.disconnect()

        # save stops file
        stopfilename = exportPath+'stops_R{:03d}_CVP{:03d}.csv'.format(seed, int(CVP*100))
        sigTools.writeStops(stopCounter, stopfilename)

        timer.stop()
        print('DONE: {}, {}, Run: {:03d}, CVP: {:03d}%, Runtime: {}, Date: {}'
              .format(modelName, tlLogic, run, int(CVP*100),
                      timer.strTime(), time.ctime()))
        sys.stdout.flush()
        return (True, x)
    except Exception as e:
        # Print if an experiment fails and provide repr of params to repeat run
        timer.stop()
        print('***FAILURE '+timer.strTime()+', '+time.ctime()+'*** '+repr(x))
        print(str(e))
        sys.stdout.flush()
        return (False, x)
    finally:
        sys.stdout.flush()