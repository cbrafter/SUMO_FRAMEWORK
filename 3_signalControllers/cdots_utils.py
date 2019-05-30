#!/usr/bin/env python
"""
@file    cdots_utils.py
@author  Craig Rafter
@date    19/08/2018

contains the functions and utility calculation for the CDOTS controller
"""
import signalControl, readJunctionData, traci
import signalTools as sigTools
from math import atan2, degrees, ceil, hypot
import numpy as np
from collections import defaultdict
import traci.constants as tc
from cooperativeAwarenessMessage import CAMChannel


class stageOptimiser():
    def __init__(self, signalController, activationArray=np.ones(7),
                 weightArray=np.ones(7)):
        self.sigCtrl = signalController
        self.activationArray = np.array([activationArray]).T
        self.weightArray = np.array([activationArray]).T
        self.Nstages = self.sigCtrl.Nstages
        self.stageCycleFreq = 2  # stage appears once in every N cycles
        self.maxRedTime = 300  # stage must appear once every 5 mins

        # Internal seeded Random Number Generator (RNG)
        self.RNG = np.random.RandomState(1)

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
        self.queueNormFactors = self.getQueueNormFactors()

        self.P_dblDeckBus = 0.7  # Probability of bus being double decker
        # Max passengers on Alexander Dennis Enviro 400 (E400)
        self.dblDeckPaxMax = 90
        # Max passengers on Alexander Dennis Enviro 200 (E200)
        self.sglDeckPaxMax = 76
        # Scaling based on time of day traffic demand
        self.busPaxScaling = {'OFF': 0.3, 'INTER': 0.6, 'PEAK': 0.9}

        # Distribution of passengers in a car, mean occupancy = 1.55 as in lit
        # self.passengerDist = 12*[1] + 6*[2] + [3, 4]
        self.carOccupancyDist = sigTools.weightedRandomDraw([1,2,3,4], 1.55)[0]
        self.occupancyDict = {}

    def getNextStageIndex(self):
        try:
            # If there's only two stages anyway, cycle to next stage
            if self.Nstages < 3:
                return (self.sigCtrl.currentStageIndex + 1) % self.Nstages

            # stage must appear once every N cycles
            stagesSinceLastCall = np.array(self.sigCtrl.stagesSinceLastCall)
            if max(stagesSinceLastCall) > self.stageCycleFreq*self.Nstages:
                return stagesSinceLastCall.argmax()

            # Stage must appear every N seconds
            timeSinceLastGreen = np.array(self.getTimeSinceLastGreen())
            if max(timeSinceLastGreen) > self.maxRedTime:
                return timeSinceLastGreen.argmax()

            # If we're free to se
            costMatrix = self.getCostMatrix()
            assert self.activationArray.shape[0] == costMatrix.shape[0]
            # All cost matrix entries need ranking except the loop
            costMatrix[:-1] = [self.rank(row) for row in rankMatrix[:-1]]
            costMatrix = self.activationArray*costMatrix

            return costMatrix.sum(axis=0).argmax()
        except:
            # If there's a problem cycle to next stage
            return (self.sigCtrl.currentStageIndex + 1) % self.Nstages

    def getCostMatrix(self):
        # determine oncoming vehicles in each lane
        self.getVehiclesPerStage()
        NumVehicles = self.getNumVehicles().astype(float)
        # Rows are specific costs, cols are stages
        rank = self.rank
        costMatrix = [self.getTimeSinceLastGreen(),
                      self.getStagesSinceLastCall(),
                      NumVehicles,
                      self.getTotalPassengers(),
                      self.getNotTurningRatio(),
                      self.getStopInfo()['total']/NumVehicles,
                      self.getWaitingInfo()['total']/NumVehicles,
                      self.getQueueLength()/self.queueNormFactors,
                      self.getLoopWaiting()]
        return np.array(costMatrix)

    def getQueueNormFactors(self):
        qNormFactors = []
        qLenMaxDict = self.getControlledRoadLength()
        for stageIndex in range(self.Nstages):
            stageEdges = self.sigCtrl.getActiveEdges(stageIndex)
            maxLen = max(qLenMaxDict[e] for e in stageEdges)
            qNormFactors.append(max(maxLen, self.sigCtrl.scanRange))
        return np.array(qNormFactors, dtype=np.float)


    def getQueueLength(self):
        queueLengths = []
        for stageIndex in range(self.Nstages):
            if stageIndex != self.sigCtrl.currentStageIndex:
                queueLengths.append(
                    self.sigCtrl.getFurthestStationaryVehicle(self.vehiclesPerStage[stageIndex]))
            else:
                queueLengths.append(0)
        return np.array(queueLengths)

    def getWaitingInfo(self):
        waitingInfo = []
        for stageIndex, vehicleSet in enumerate(self.vehiclesPerStage):
            totalWait = 0.0
            maxWait = 0.0
            # vehicle set is empty for active lane so wont process
            for vehID in vehicleSet:
                waitTime = self.sigCtrl.stopCounter.subResults[vehID][tc.VAR_WAITING_TIME]
                totalWait += waitTime
                maxWait = max(maxWait, waitTime)
            waitingInfo.append({'total': np.array(totalWait), 
                                'max': np.array(maxWait)})
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
            stopInfo.append({'total': np.array(totalStops), 
                             'max': np.array(maxStops)})
        return stopInfo


    def getTotalPassengers(self):
        totalPassengers = []
        for vehicleSet in self.vehiclesPerStage:
            paxCount = 0
            # vehicle set is empty for active lane so wont process
            for vehID in vehicleSet:
                try:
                    paxCount += self.occupancyDict[vehID]
                except KeyError:
                    vType = self.sigCtrl.emissionCounter.vTypeDict[vehID]
                    if 'car' in vType:
                        # DfT NTS0905 occupancy avg 1.55. Here we achieve this by 
                        # having cars with 1 or 2 pax from weighted uniform dist
                        # Npassengers = int(1+(round(rng.rand()<0.55)))
                        # OR
                        # From choice distribution with weighted numbers 1-4
                        # and mean 1.55 
                        Npassengers = self.RNG.choice(self.carOccupancyDist)
                    elif 'lgv' in vType:
                        Npassengers = 1 
                    elif 'hgv' in vType:
                        Npassengers = 1 
                    elif 'motorcycle' in vType:
                        Npassengers = 1 
                    elif 'bus' in vType:
                        isDblDecker = self.RNG.rand() <= self.P_dblDeckBus
                        if isDblDecker:
                            Npassengers = (self.dblDeckPaxMax
                                           * self.busPaxScaling[self.sigCtrl.mode])
                        else:
                            Npassengers = (self.sglDeckPaxMax
                                           * self.busPaxScaling[self.sigCtrl.mode])
                    else:
                        Npassengers = 1 

                    paxCount += Npassengers
                    self.occupancyDict[vehID] = Npassengers
            totalPassengers.append(paxCount)
        return np.array(totalPassengers)

    def getVehicleTypeCost(self):
        vTypeCost = []
        for vehicleSet in self.vehiclesPerStage:
            totalCost = 0.0
            # vehicle set is empty for active lane so wont process
            for vehID in vehicleSet:
                vType = self.sigCtrl.emissionCounter.vTypeDict[vehID]
                totalCost += self.vTypeWeight[vType.split('_')[-1]]
            vTypeCost.append(totalCost)
        return np.array(vTypeCost)

    def getNumVehicles(self):
        numVehicles = [len(vSet) for vSet in self.vehiclesPerStage]
        return np.array(numVehicles)

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

        return np.array(stageWaiting)

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
            if len(vehicleSet) > 0:
                nonTurningRatio.append(1.0 - (Nturning/float(len(vehicleSet))))
            else:
                nonTurningRatio.append(1)
        return np.array(nonTurningRatio)

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

    def getStagesSinceLastCall(self):
        return np.array(self.sigCtrl.stagesSinceLastCall)

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
            emissionInfo.append({'total': np.array(totalEmissions), 
                                 'max': np.array(maxEmissions)})
        return emissionInfo

    def getVehiclesPerStage(self):
        self.vehiclesPerStage = []
        for stageIndex in range(self.Nstages):
            if stageIndex != self.sigCtrl.currentStageIndex:
                self.vehiclesPerStage.append(self.sigCtrl.getOncomingVehicles(stageIndex))
            else:
                self.vehiclesPerStage.append([])

        return self.vehiclesPerStage

    def getControlledRoadLength(self):
        qLenMaxDict = defaultdict(float)
        for edge in self.sigCtrl.controlledEdges.keys():
            for lane in self.sigCtrl.controlledEdges[edge]:
                qLenMaxDict[edge] += traci.lane.getLength(lane+'_0')
        return qLenMaxDict 

    def getSpeedCost(self):
        pass

    def getAccelCost(self):
        pass

    def getTravelTimeInfo(self):
        # total, min, and max travel time for waiting vehicles
        pass

    def getTravelDistanceInfo(self):
        # total, min, max distace travelled by waiting vehicles
        pass

    def getEmergencyVehicleStatus(self):
        "Detect and provision for emergency vehicles"
        pass

    def sharedTransportDetection(self):
        "detect public or shared transport and allow priority"
        pass 

    def getSpecialVehicleCost(self):
        pass

    def relNorm(self, x):
        data = np.array(x)
        return data.astype(float)/data.max()

    def rank(self, costArray):
        costs = np.array(costArray)
        rankArray = np.zeros_like(costArray)
        costAlloc = self.Nstages - 2  # Nstages must be at least 3 for this to happen anyway
        for idx in costs.argsort()[::-1]:
            # only assign costs where to stages where there is data
            if costs[idx] < 0:
                rankArray[idx] = 0
            else:
                rankArray[idx] = max(0, costAlloc)
            costAlloc -= 1
        return rankArray
