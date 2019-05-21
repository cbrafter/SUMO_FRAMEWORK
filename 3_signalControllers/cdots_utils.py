#!/usr/bin/env python
"""
@file    scoarutils.py
@author  Craig Rafter
@date    19/08/2018

contains the functions and utility calculation for the SCOAR controller
"""
import signalControl, readJunctionData, traci
import signalTools as sigTools
from math import atan2, degrees, ceil, hypot
import numpy as np
from collections import defaultdict
import traci.constants as tc
from cooperativeAwarenessMessage import CAMChannel


class stageOptimiser():
    def __init__(self, signalController):
        self.sigCtrl = signalController
        self.Nstages = self.sigCtrl.Nstages

        # Emission constants
        self.CO2 = tc.VAR_CO2EMISSION
        self.CO = tc.VAR_COEMISSION
        self.HC = tc.VAR_HCEMISSION
        self.PMX = tc.VAR_PMXEMISSION
        self.NOX = tc.VAR_NOXEMISSION
        self.FUEL = tc.VAR_FUELCONSUMPTION
        self.emissionList = [self.CO2, self.CO, self.HC,
                             self.PMX, self.NOX, self.FUEL]

        # vehicle type weighting
        self.vTypeWeight = {'car': 1, 'motorcycle': 1,
                            'lgv': 1, 'hgv': 1, 'bus': 1}

        self.numLanesServed = self.getNumLanesServed()

    def getNextStageIndex(self):
        try:
            laneCosts = np.array(self.getLaneCosts())
            return laneCosts.argmax()
        except:
            return None

    def getLaneCosts(self):
        # determine oncoming vehicles in each lane
        self.getVehiclesPerStage()
        costs = []
        for stageIndex in range(self.Nstages):
            # Only calculate costs for the inactive stages
            if stageIndex != self.sigCtrl.currentStageIndex:
                cost.append(1)
            else:
                costs.append(0) 
        return costs

    def getQueueLength(self):
        queueLengths = []
        for stageIndex in range(self.Nstages):
            if stageIndex != self.sigCtrl.currentStageIndex:
                queueLengths.append(
                    self.sigCtrl.getFurthestStationaryVehicle(self.vehiclesPerStage[stageIndex]))
            else:
                queueLengths.append(0)
        return queueLengths

    def getWaitinginfo(self):
        waitingInfo = []
        for stageIndex, vehicleSet in enumerate(self.vehiclesPerStage):
            totalWait = 0.0
            maxWait = 0.0
            # vehicle set is empty for active lane so wont process
            for vehID in vehicleSet:
                waitTime = self.sigCtrl.stopCounter.subResults[vehID][tc.VAR_WAITING_TIME]
                totalWait += waitTime
                maxWait = max(maxWait, waitTime)
            waitingInfo.append({'total': totalWait, 'max': maxWait})
        return waitingInfo

    def getStopInfo(self):
        stopInfo = []
        for vehicleSet in self.vehiclesPerStage:
            totalStops = 0.0
            maxStops = 0.0
            # vehicle set is empty for active lane so wont process
            for vehID in vehicleSet:
                Nstops = self.sigCtrl.stopCounter.stopCountDict[vehID]
                totalStops += Nstops
                maxStops = max(maxStops, Nstops)
            stopInfo.append({'total': totalStops, 'max': maxStops})
        return stopInfo

    def getSpeedCost(self):
        pass

    def getAccelCost(self):
        pass

    def getTotalPassengers(self):
        pass

    def getVehicleTypeCost(self):
        vTypeCost = []
        for vehicleSet in self.vehiclesPerStage:
            totalCost = 0.0
            # vehicle set is empty for active lane so wont process
            for vehID in vehicleSet:
                vType = self.sigCtrl.emissionCounter.vTypeDict[vehID]
                totalCost += self.vTypeWeight[vType.split('_')[-1]]
            vTypeCost.append(totalCost)
        return vTypeCost

    def getSpecialVehicleCost(self):
        pass

    def getLoopWaiting(self):
        stageWaiting = []
        flowConst = tc.LAST_STEP_TIME_SINCE_DETECTION
        for stageIndex in range(self.Nstages):
            if stageIndex != self.sigCtrl.currentStageIndex:
                activeLanes = self.sigCtrl.getActiveLanes()
                detect = 0
                edges = sigTools.unique([lane.split('_')[0] for lane in activeLanes])
                # see if a loop has been triggered recently. If so there might
                # be a vehicle waiting, only loop until confirmation
                for edge in edges:
                    for loop in self.laneInductors[edge]:
                        if self.subResults[loop][flowConst] < 0.5:
                            detect = 1
                            break
                    if detect:
                        break

                stageWaiting.append(detect)
            else:
                stageWaiting.append(0)

        return stageWaiting

    def getNotTurningRatio(self):
        nonTurningRatio = []
        for vehicleSet in self.vehiclesPerStage:
            Nturning = 0.0  #  num vehicles that want to turn
            # Ndirect = 0.0  #  num vehicles that don't want to turn
            # vehicle set is empty for active lane so won't process
            for vehID in vehicleSet:
                signal = self.sigCtrl.CAM.receiveData[vehID]['signal']
                if signal['BLINKER_LEFT'] or signal['BLINKER_RIGHT']:
                    Nturning += 1
            nonTurningRatio.append(1.0 - (Nturning/float(len(vehicleSet))))
        return nonTurningRatio

    def getNumLanesServed(self):
        numLanes = []
        for stageIndex, time in enumerate(self.sigCtrl.stageLastCallTime):
            if stageIndex != self.sigCtrl.currentStageIndex:
                numLanes.append(len(self.sigCtrl.getActiveLanes(stageIndex)))
            else:
                numLanes.append(0)
        return np.array(numLanes)

    def getTimeSinceLastGreen(self):
        timeDeltas = []
        for stageIndex, time in enumerate(self.sigCtrl.stageLastCallTime):
            if stageIndex != self.sigCtrl.currentStageIndex:
                timeDeltas.append(float(self.sigCtrl.TIME_SEC) - time)
            else:
                timeDeltas.append(0.0)
        return np.array(timeDeltas)

    def getEmissions(self):
        emissionInfo = []
        for vehicleSet in self.vehiclesPerStage:
            totalEmissions = {k: 0.0 for k in emissionList}
            maxEmissions = {k: 0.0 for k in emissionList}
            # vehicle set is empty for active lane so wont process
            for vehID in vehicleSet:
                emDict = self.sigCtrl.emissionCounter.emissionCountDict[vehID]
                for emission in emissionList:
                    totalEmissions[emission] += emDict[emission]
                    maxEmissions[emission] = max(maxEmissions[emission], emDict[emission])
            emissionInfo.append({'total': totalEmissions, 'max': maxEmissions})
        return emissionInfo

    def getVehiclesPerStage(self):
        self.vehiclesPerStage = []
        for stageIndex in range(self.Nstages):
            if stageIndex != self.sigCtrl.currentStageIndex:
                self.vehiclesPerStage.append(self.sigCtrl.getOncomingVehicles(stageIndex))
            else:
                self.vehiclesPerStage.append([])

    def relNorm(self, x):
        data = np.array(x)
        return data.astype(float)/data.max()
