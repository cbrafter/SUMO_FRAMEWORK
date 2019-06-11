# -*- coding: utf-8 -*-
import sys
import os
import shutil
import socket
import time
from sumoConfigGen import sumoConfigGen
sys.path.insert(0, '../1_sumoAPI')
import sumoConnect
import readJunctionData
sys.path.insert(0, '../3_signalControllers')
import fixedTimeControl
import TRANSYT
import HybridVAControl
import CDOTS
import traci
import signalTools as sigTools
import traceback


def simulation(configList, GUIbool=False):
    try:
        timer = sigTools.simTimer()
        timer.start()
        if len(configList) == 6:
            modelName, tlLogic, CVP, run, pedStage, procID = configList
        else:
            modelName, tlLogic, CVP, run, pedStage, activationArray, procID = configList
        # split returns list so whether or not selly in name right base given 
        modelBase = modelName.split('_')[0]
        hostname = socket.gethostname()
        model = '../2_models/{}_{}_{}/'.format(modelBase, hostname, procID)
        simport = 8812 + procID
        seed = int(run)
        stepSize = 0.1
        configFile = model + modelBase + ".sumocfg"

        print('STARTING: {}, {}, Run: {:03d}, CVP: {:03d}%, Ped: {}, Date: {}'
              .format(modelName, tlLogic, run, int(CVP*100), pedStage, time.ctime()))
        sys.stdout.flush()

        # Configure the Map of controllers to be run
        tlControlMap = {'fixedTime': fixedTimeControl.fixedTimeControl,
                        'TRANSYT': TRANSYT.TRANSYT,
                        'GPSVA': HybridVAControl.HybridVAControl,
                        'HVA': HybridVAControl.HybridVAControl,
                        'HVAslow': HybridVAControl.HybridVAControl,
                        'GPSVAslow': HybridVAControl.HybridVAControl,
                        'CDOTS': CDOTS.CDOTS,
                        'CDOTSslow': CDOTS.CDOTS}
        tlController = tlControlMap[tlLogic]

        # Define output folder
        pedStr = '_ped' if pedStage else ''
        if 'CDOTS' in tlLogic:
            activStr = ''.join(str(bit) for bit in activationArray)
            exportPath = ('/hardmem/results/{}{}/{}/{}/'
                          .format(tlLogic, pedStr, modelName, activStr))
        else:
            exportPath = ('/hardmem/results/{}{}/{}/'
                          .format(tlLogic, pedStr, modelName))

        # Check if model copy for this process exists
        if not os.path.isdir(model):
            shutil.copytree('../2_models/{}/'.format(modelBase), model)
            time.sleep(1)  # sleep to make sure files copied on HPC

        # this is relative to script not cfg file
        # try to make dir but keep going if other process created it already
        if not os.path.exists(exportPath):
            try:
                os.makedirs(exportPath)
            except:
                time.sleep(1)  # sleep to make sure folder created

        # Edit the the output filenames in sumoConfig
        sumoConfigGen(modelName, configFile, exportPath, 
              CVP=CVP, stepSize=stepSize, 
              run=seed, port=simport, seed=seed)

        # Connect to model
        connector = sumoConnect.sumoConnect(configFile, gui=GUIbool, port=simport)
        connector.launchSumoAndConnect()

        # Get junction data
        if 'selly' in model:
            junctionFile = model + modelBase + ".t15.xml"
        else:
            junctionFile = model + modelBase + ".jcn.xml"

        jd = readJunctionData.readJunctionData(junctionFile)
        junctionsList = jd.getJunctionData()

        # Add controller models to junctions
        controllerList = []
        # Turn loops off if CAV ratio > 50%
        for junction in junctionsList:
            CAMmod = 1.0 if 'slow' in tlLogic else False
            loopCtrl = 'HVA' in tlLogic
            noise = 'slow' in tlLogic
            PER = 0.5 if noise else 0.0
            if ('HVA' in tlLogic) or ('GPSVA' in tlLogic): 
                controllerList.append(tlController(junction, 
                                                   loopIO=loopCtrl,
                                                   CAMoverride=CAMmod,
                                                   model=modelBase,
                                                   PER=PER, noise=noise,
                                                   pedStageActive=pedStage))
            elif 'CDOTS' in tlLogic:
                controllerList.append(tlController(junction, 
                                                   CAMoverride=CAMmod,
                                                   model=modelBase,
                                                   PER=PER, noise=noise,
                                                   pedStageActive=pedStage,
                                                   activationArray=activationArray))
            else:
                controllerList.append(tlController(junction, pedStageActive=pedStage))

        # Step simulation while there are vehicles
        # we use traci method for initial value in case begin != 0
        simTime, simActive = traci.simulation.getCurrentTime(), True
        timeLimit = 1*60*60  # 1 hours in seconds for time limit
        limitExtend = 15*60 # check again in 15 mins if things seem ok
        stopCounter = sigTools.StopCounter()
        emissionCounter = sigTools.EmissionCounter()
        stopFilename = exportPath+'stops_R{:03d}_CVP{:03d}.csv'.format(seed, int(CVP*100))
        emissionFilename = exportPath+'emissions_R{:03d}_CVP{:03d}.csv'.format(seed, int(CVP*100))
        timeDelta = int(1000*stepSize)
        oneMinute = 60*1000  # one minute in simulation 60sec im msec

        # Flush print buffer
        sys.stdout.flush()

        while simActive:
            traci.simulationStep()
            simTime += timeDelta
            stopCounter.getStops()
            emissionCounter.getEmissions(simTime)

            for controller in controllerList:
                if 'CDOTS' in tlLogic:
                    controller.process(time=simTime, stopCounter=stopCounter, 
                                       emissionCounter=emissionCounter)
                else:
                    controller.process(time=simTime)

            # reduce calls to traci to 1 per simulation min to improve performance
            # flag will always be positive int while there are vehicles no need for else
            if not simTime % oneMinute: 
                simActive = traci.simulation.getMinExpectedNumber()
                # stop sim to free resources if taking longer than ~10 hours
                # i.e. the sim is gridlocked
                if timer.runtime() > timeLimit:
                    stopCounter.writeStops(stopFilename)
                    emissionCounter.writeEmissions(emissionFilename)
                    if sigTools.isSimGridlocked(modelBase, simTime):
                        connector.disconnect()
                        raise RuntimeError("RuntimeError: GRIDLOCK")
                    else:
                        timeLimit += limitExtend

        # Disconnect from current configuration
        connector.disconnect()

        # save stops and emissions files
        stopCounter.writeStops(stopFilename)
        emissionCounter.writeEmissions(emissionFilename)

        timer.stop()
        print('DONE: {}, {}, Run: {:03d}, CVP: {:03d}%, Ped: {} Runtime: {}, Date: {}'
              .format(modelName, tlLogic, run, int(CVP*100), pedStage,
                      timer.strTime(), time.ctime()))
        sys.stdout.flush()
        return (True, configList)
    except Exception as e:
        # Print if an experiment fails and provide repr of params to repeat run
        timer.stop()
        print('***FAILURE '+timer.strTime()+', '+time.ctime()+'*** '+repr(configList))
        print(str(e))
        traceback.print_exc()
        sys.stdout.flush()
        return (False, configList)
    finally:
        stopCounter.writeStops(stopFilename)
        sys.stdout.flush()
        # remove spawned model folder
        try:
            if os.path.isdir(model):
                shutil.rmtree(model)
        except:
            print('Could not remove folder: '+ model)
