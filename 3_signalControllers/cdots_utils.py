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
import traceback


class stageOptimiser():
    def __init__(self, signalController, activationArray=np.ones(7),
                 weightArray=np.ones(7, dtype=float), sync=False,
                 syncFactor=0.25, syncMode='PS'):
        self.sigCtrl = signalController
        # dim expanstion maxes array to col vector
        # no np.newaxis as lists can be expanded with the function
        self.activationArray = np.expand_dims(activationArray, 1)
        try:
            self.weightArray = np.array(activationArray, dtype=float)
            self.weightArray[self.weightArray>0] = weightArray
            self.weightArray = np.expand_dims(self.weightArray, 1)
        except:
            self.weightArray = np.expand_dims(activationArray, 1)

        self.Nstages = self.sigCtrl.Nstages
        self.stageCycleFreq = 2  # stage appears once in every N cycles
        self.maxRedTime = 300  # stage must appear once every 5 mins
        # Sync settings
        self.sync = sync
        self.syncStrength = syncFactor*self.Nstages
        self.syncMode = syncMode
        self.syncModeWeights = {'P': [1, 0], 'PS': [1, 1], 'Ps': [1, 0.5]}

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

        # Distribution of passengers in a car, mean occupancy = 1.55 as in lit
        # self.passengerDist = 12*[1] + 6*[2] + [3, 4]
        self.carOccupancyDist = sigTools.weightedRandomDraw([1,2,3,4], 1.55)[0]
        self.occupancyDict = {}

    def getNextStageIndex(self, mode='REL'):
        try:
            # If there's only two stages anyway, cycle to next stage OR
            # If there are no CAVs providing control data, cycle to next stage
            if self.Nstages < 3 or self.sigCtrl.numCAVs < 1:
                # if self.sigCtrl.junctionData.id == 'junc3': print("Too few stages")
                return (self.sigCtrl.currentStageIndex + 1) % self.Nstages

            # stage must appear once every N cycles
            # Override on cycle appearence only
            stagesSinceLastCall = np.array(self.sigCtrl.stagesSinceLastCall)
            if max(stagesSinceLastCall) > self.stageCycleFreq*self.Nstages:
                # if self.sigCtrl.junctionData.id == 'junc3': print("CYCLE OVERRIDE")
                return stagesSinceLastCall.argmax()

            # Stage must appear every N seconds
            # timeSinceLastGreen = np.array(self.getTimeSinceLastGreen())
            # if max(timeSinceLastGreen) > self.maxRedTime:
            #     if self.sigCtrl.junctionData.id == 'junc3': print("Time override")
            #     return timeSinceLastGreen.argmax()

            # Get utility matrix if the special cases aren't set
            utilMatrix = self.getUtilityMatrix()
            assert self.activationArray.shape[0] == utilMatrix.shape[0]
            rankMatrix = utilMatrix.copy()
            if mode == 'RANK':
                # All cost matrix entries need ranking except the loop
                rankMatrix[:-1] = [self.rank(row) for row in rankMatrix[:-1]]
            else:
                rankMatrix[:-1] = [self.relNorm(row) for row in rankMatrix[:-1]]
                rankMatrix[rankMatrix < 0] = 0
            # blank out 
            rankMatrix = self.activationArray*rankMatrix
            rankMatrix = self.weightArray*rankMatrix

            # if self.sigCtrl.junctionData.id == 'junc3':
            #     np.set_printoptions(precision=3, suppress=True)
            #     print(self.weightArray.T)
            #     print(utilMatrix)
            #     print(rankMatrix)
            #     print(rankMatrix.sum(axis=0))
            #     print(rankMatrix.sum(axis=0).argmax())

            # Add tiny amount of uniform random noise to randomise argmax when
            # ranks are tied
            if self.sync:
                rankTotal = rankMatrix.sum(axis=0) + self.syncStrength*self.syncVector
                # make sure the sync doesn't cause the same stage twice in a row
                rankTotal[self.sigCtrl.currentStageIndex] = 0.0
                rankTotal = self.tieBreak(rankTotal)
                # if self.sigCtrl.junctionData.id == 'junc3': 
                #     print(self.syncVector)
                #     print(rankMatrix.sum(axis=0).argmax(), rankTotal.argmax())
            else:
                rankTotal = self.tieBreak(rankMatrix.sum(axis=0))
            return rankTotal.argmax()
        except Exception as e:
            # If there's a problem cycle to next stage
            print(str(e))
            traceback.print_exc()
            return (self.sigCtrl.currentStageIndex + 1) % self.Nstages

    def getUtilityMatrix(self):
        # determine oncoming vehicles in each lane
        self.getVehiclesPerStage()
        NumVehicles = self.getNumVehicles().astype(float)
        # need abs so dividing -1's don't incur sign change and no div by 0
        absNumVehicles = np.abs(NumVehicles)
        stopInfo = np.array([data['total'] for data in self.getStopInfo()])
        waitInfo = np.array([data['total'] for data in self.getWaitingInfo()])
        # Rows are specific costs, cols are stages
        # We omit stageSinceLastCall as it duplicates getTimeSinceLastGreen
        # and we already have an override for it if it gets too high
        costMatrix = [self.getTimeSinceLastGreen(),
                      NumVehicles,
                      self.getTotalPassengers(),
                      stopInfo/absNumVehicles,
                      waitInfo/absNumVehicles,
                      self.getQueueLength()/self.queueNormFactors,
                      self.getNotTurningRatio()]
                      #self.getLoopWaiting()]
        return np.array(costMatrix)

    def getQueueNormFactors(self):
        # returns the maximum length a queue can have in each stage
        qNormFactors = []
        qLenMaxDict = self.getControlledRoadLength()
        for stageIndex in range(self.Nstages):
            stageEdges = self.sigCtrl.getActiveEdges(stageIndex)
            maxLen = max(qLenMaxDict[e] for e in stageEdges)
            qNormFactors.append(min(maxLen, self.sigCtrl.scanRange))
        return np.array(qNormFactors, dtype=np.float)

    def getQueueLength(self):
        queueLengths = []
        for stageIndex in range(self.Nstages):
            if stageIndex != self.sigCtrl.currentStageIndex:
                vData = self.sigCtrl.getFurthestStationaryVehicle(
                            self.vehiclesPerStage[stageIndex])
                # append dist only, is -1 if none anyway
                queueLengths.append(vData[1])
            else:
                queueLengths.append(-1)
        return np.array(queueLengths)

    def getWaitingInfo(self):
        waitingInfo = []
        for vehicleSet in self.vehiclesPerStage:
            init = 0.0 if len(vehicleSet) else -1
            totalWait = init
            maxWait = init
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
            init = 0.0 if len(vehicleSet) else -1
            totalStops = init
            maxStops = init
            # vehicle set is empty for active lane so wont process
            for vehID in vehicleSet:
                Nstops = self.sigCtrl.stopCounter.stopCountDict[vehID]
                totalStops += Nstops
                maxStops = max(maxStops, Nstops)
            stopInfo.append({'total': np.array(totalStops), 
                             'max': np.array(maxStops)})
        return stopInfo

    def getCarPassengers(self):
        # DfT NTS0905 occupancy avg 1.55. Here we achieve this by 
        # having cars with 1 or 2 pax from weighted uniform dist
        # Npassengers = int(1+(round(rng.rand()<0.55)))
        # OR From choice distribution with weighted numbers 1-4
        # and mean 1.55 
        return self.RNG.choice(self.carOccupancyDist)

    def getBusPassengers(self, maxOccupancy=90):
        # Define boundaries for 3 quantiles (tertile)
        Tertile1 = int(0.33*maxOccupancy)
        Tertile2 = int(0.67*maxOccupancy)
        if self.sigCtrl.mode == 'OFF':
            return self.RNG.randint(1, Tertile1)
        elif self.sigCtrl.mode == 'INTER':
            return self.RNG.randint(Tertile1, Tertile2)
        elif self.sigCtrl.mode == 'PEAK':
            return self.RNG.randint(Tertile2, maxOccupancy)
        else:
            return self.RNG.randint(1, maxOccupancy)

    def getTotalPassengers(self):
        totalPassengers = []
        for vehicleSet in self.vehiclesPerStage:
            paxCount = 0 if len(vehicleSet) else -1
            # vehicle set is empty for active lane so wont process
            for vehID in vehicleSet:
                try:
                    paxCount += self.occupancyDict[vehID]
                except KeyError:
                    vType = self.sigCtrl.emissionCounter.vTypeDict[vehID]
                    if 'car' in vType:
                        Npassengers = self.getCarPassengers()
                    elif 'lgv' in vType:
                        Npassengers = 1 
                    elif 'hgv' in vType:
                        Npassengers = 1 
                    elif 'motorcycle' in vType:
                        Npassengers = 1 
                    elif 'bus' in vType:
                        isDblDecker = self.RNG.rand() <= self.P_dblDeckBus
                        if isDblDecker:
                            Npassengers = self.getBusPassengers(self.dblDeckPaxMax)
                        else:
                            Npassengers = self.getBusPassengers(self.sglDeckPaxMax)
                    else:
                        Npassengers = 1 

                    paxCount += Npassengers
                    self.occupancyDict[vehID] = Npassengers
            totalPassengers.append(paxCount)
        return np.array(totalPassengers)

    def getVehicleTypeCost(self):
        vTypeCost = []
        for vehicleSet in self.vehiclesPerStage:
            totalCost = 0 if len(vehicleSet) else -1
            # vehicle set is empty for active lane so wont process
            for vehID in vehicleSet:
                vType = self.sigCtrl.emissionCounter.vTypeDict[vehID]
                totalCost += self.vTypeWeight[vType.split('_')[-1]]
            vTypeCost.append(totalCost)
        return np.array(vTypeCost)

    def getNumVehicles(self):
        numVehicles = []
        for vehicleSet in self.vehiclesPerStage:
            Nveh = len(vehicleSet)
            numVehicles.append(Nveh if Nveh else -1)
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
                    for loop in self.sigCtrl.laneInductors[edge]:
                        if self.sigCtrl.subResults[loop][flowConst] < 0.5:
                            detect = 1
                            break
                    if detect:
                        break
                if len(self.sigCtrl.laneInductors):
                    stageWaiting.append(detect)
                else:
                    # Doesn't get ranked so 0 not -1
                    stageWaiting.append(0)
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
            
            if len(vehicleSet):
                nonTurningRatio.append(1.0 - (Nturning/float(len(vehicleSet))))
            else:
                nonTurningRatio.append(-1)
        return np.array(nonTurningRatio)

    def getNumLanesServed(self):
        # get number of lanes served by each stage
        numLanes = []
        for stageIndex, time in enumerate(self.sigCtrl.stageLastCallTime):
            if stageIndex != self.sigCtrl.currentStageIndex:
                numLanes.append(len(self.sigCtrl.getActiveLanes(stageIndex)))
            else:
                numLanes.append(0)
        return np.array(numLanes)

    def getTimeSinceLastGreen(self):
        # Work out the time difference now and when each stage was last called
        timeDeltas = []
        for stageIndex, time in enumerate(self.sigCtrl.stageLastCallTime):
            if stageIndex != self.sigCtrl.currentStageIndex:
                timeDeltas.append(float(self.sigCtrl.TIME_SEC) - time)
            else:
                timeDeltas.append(0.0)
        return np.array(timeDeltas)

    def getStagesSinceLastCall(self):
        # access stagesSinceLastCall from the signal controller as array
        return np.array(self.sigCtrl.stagesSinceLastCall)

    def getEmissions(self):
        # Calculate total and max emissions for waiting vehicles
        emissionInfo = []
        for vehicleSet in self.vehiclesPerStage:
            # initial value -1 if there is no data for this stage
            init = 0.0 if len(vehicleSet) else -1
            totalEmissions = {k: init for k in emissionList}
            maxEmissions = {k: init for k in emissionList}
            # vehicle set is empty for active lane so won't process
            for vehID in vehicleSet:
                emDict = self.sigCtrl.emissionCounter.emissionCountDict[vehID]
                for emission in emissionList:
                    totalEmissions[emission] += emDict[emission]
                    maxEmissions[emission] = max(maxEmissions[emission], emDict[emission])
            emissionInfo.append({'total': np.array(totalEmissions), 
                                 'max': np.array(maxEmissions)})
        return emissionInfo

    def getVehiclesPerStage(self):
        # get the oncoming vehicles associated with each stage
        self.vehiclesPerStage = []
        for stageIndex in range(self.Nstages):
            # Only calculate for inactive stages
            if stageIndex != self.sigCtrl.currentStageIndex:
                self.vehiclesPerStage.append(self.sigCtrl.getOncomingVehicles(stageIndexOverride=stageIndex))
            else:
                self.vehiclesPerStage.append([])
        # if self.sigCtrl.junctionData.id == 'junc3': print(self.vehiclesPerStage)
        return self.vehiclesPerStage

    def getControlledRoadLength(self):
        # Return max length of road for eahc controlled stage
        qLenMaxDict = defaultdict(float)
        for edge in self.sigCtrl.controlledEdges.keys():
            for lane in self.sigCtrl.controlledEdges[edge]:
                qLenMaxDict[edge] += traci.lane.getLength(lane+'_0')
        return qLenMaxDict 

    def getSpeedCost(self):
        # Get speed limits for each stage
        pass

    def getAccelCost(self):
        # Work out which queue will accelerate faster
        pass

    def getTravelTimeInfo(self):
        # total, min, and max travel time for waiting vehicles
        pass

    def getTravelDistanceInfo(self):
        # total, min, max distace travelled by waiting vehicles
        pass

    def getEmergencyVehicleStatus(self):
        # Detect and provision for emergency vehicles
        pass

    def sharedTransportDetection(self):
        # detect public or shared transport and allow priority
        pass 

    def getSpecialVehicleCost(self):
        # Make provisions for emergency vehicles or other vehicles that need
        # want prioritisation
        pass

    def getSpeedFactor(self):
        # penalty for users who exceed the speed limit by more than 10%
        pass

    def relNorm(self, data):
        # Norm data based on the maximum data
        divisor = abs(data.max())
        # set negative divisors to 1.0 so they don't affect result
        divisor = float(divisor) if divisor > 1e-6 else 1.0
        result = data/divisor  # divide all quantities by max value
        # All negative values to zero so they don't contribute to sum
        result[result < 0] = 0
        return result

    def rank(self, costArray):
        # Podium rank the data
        costs = self.tieBreak(costArray)
        rankArray = np.zeros_like(costArray)
        # Nstages must be at least 3 for this to happen anyway
        costAlloc = self.Nstages - 2
        for idx in costs.argsort()[::-1]:
            # only assign costs where to stages where there is data
            if costs[idx] < 0:
                rankArray[idx] = 0
            else:
                rankArray[idx] = max(0, costAlloc)
            costAlloc -= 1
        return rankArray

    def tieBreak(self, vec):
        # Adds a tiny amount of random noise to the rank vector so that argmax
        # doesn't bias towards the first index with max value
        randomness = self.RNG.rand(*vec.shape)*1e-6
        return vec + randomness

    def getStageIDMap(self):
        # map stage list index to stage ID
        stageIdMap = {}
        stageData = self.sigCtrl.junctionData.stages[self.sigCtrl.mode]
        for i, stage in enumerate(stageData):
            stageIdMap[stage.id] = i
        return stageIdMap

    def turnCountFilter(self, direction, turnCounts):
        if direction == 'D' and turnCounts['DIRECT'] > 0:
            return self.syncModeWeights[self.syncMode][0]
        elif direction == 'L' and turnCounts['LEFT'] > 0:
            return self.syncModeWeights[self.syncMode][1]
        elif direction == 'R' and turnCounts['RIGHT'] > 0:
            return self.syncModeWeights[self.syncMode][1]
        else:
            return 0

    def getSyncVector(self):
        try:
            # Map stage ID to the current sequence
            stageIDMap = self.getStageIDMap()
            # Need to calculate sync vector every time as stage order may change
            # Type must be into for bitwise OR later on
            self.syncVector = np.zeros(self.Nstages, dtype=int)
            # for every junction ID and object in the dict of junctions we sync with
            for adjID, adjJunc in self.sigCtrl.syncJuncs.items():
                syncVector = np.zeros(self.Nstages, dtype=int)
                # Get the junction ID appended with the ID of the current stage
                # from the junction to sync with
                adjStageID = adjJunc.getSyncString()
                adjStageIDint = int(adjStageID.split('_')[-1])
                # If the target junction is less than halfway through its max
                # stage then its less likely to change so receive vehicles
                stageCutoff = 0.5*adjJunc.getAvgStageTime()[adjStageIDint]
                if adjJunc.elapsedTime <= stageCutoff:
                    turnCounts = adjJunc.stageOptimiser.getTurnCounts()
                    # get the sync relationships from the SOURCE to the SINK
                    # SRC: ADJ JUNC | SNK: THIS JUNC
                    for snkStage, coordStages in self.sigCtrl.syncRels.items():
                        snkStageID = snkStage.split('_')[-1]
                        snkStageIDint = int(snkStageID)
                        # check if we have stages in the adjacent junctions
                        # sync strings
                        for srcStage in coordStages:
                            # If this junction present in the target stages sync strings
                            # only sync if its the surrent stage of the adj junc
                            if adjStageID not in srcStage:
                                continue
                            # get the stage id and flow direction for the stages
                            # that will send vehicles to the adjacent junction
                            srcStageID, direction = srcStage.split('_')[1:]
                            turns = turnCounts[int(srcStageID)]
                            # Only sync if there are vehicles travelling ato
                            # this junction from the sync stage
                            # turns = {'DIRECT':1,'LEFT':1, 'RIGHT':1}
                            syncVector[stageIDMap[snkStageID]] =\
                                max(syncVector[stageIDMap[snkStageID]],
                                    self.turnCountFilter(direction, turns))
                # The target junction is over halfway through its stage so is 
                # likely to change soon. Therefore send it vehicles
                else:
                    # As we're sending vehicles, get this junctions turn counts
                    turnCounts = self.sigCtrl.stageOptimiser.getTurnCounts()
                    # get the sync relationships for the adjacent junction
                    # SRC: THIS JUNC | SNK: ADJ JUNC
                    for snkStage, coordStages in adjJunc.syncRels.items():
                        # check if we have stages in the adjacent junctions
                        # sync strings i.e. stage we can send vehicles to
                        for srcStage in coordStages:
                            # If this junction present in the target stages' sync strings
                            if self.sigCtrl.junctionData.id not in srcStage:
                                continue
                            # get the stage id and flow direction for the stages
                            # that will send vehicles to the adjacent junction
                            srcStageID, direction = srcStage.split('_')[1:]
                            turns = turnCounts[int(srcStageID)]
                            # Only sync if there are vehiles travelling along the
                            # sync path
                            # turns = {'DIRECT':1,'LEFT':1, 'RIGHT':1}
                            syncVector[stageIDMap[srcStageID]] =\
                                max(syncVector[stageIDMap[srcStageID]],
                                    self.turnCountFilter(direction, turns))
                # bitwise or the stage vectors to capture all syncing stages
                # need np.maximum to do max along array
                self.syncVector = np.maximum(self.syncVector, syncVector)
                if self.sigCtrl.junctionData.id == 'junc3':
                    print(self.syncVector, adjJunc.elapsedTime <= stageCutoff,
                          self.sigCtrl.mode)
        except Exception as e:
            self.syncVector = np.zeros(self.Nstages)
            print(self.sigCtrl.junctionData.id, str(e))
            traceback.print_exc()
            # raise(e)

    def getTurnCounts(self):
        turnCounts = []
        if not hasattr(self, 'vehiclesPerStage'):
            self.getVehiclesPerStage()
        for vehicleSet in self.vehiclesPerStage:
            turnDict = defaultdict(int)
            turnDict['DIRECT'] = 0
            turnDict['LEFT'] = 0
            turnDict['RIGHT'] = 0
            # Ndirect = 0.0  #  num vehicles that don't want to turn
            # vehicle set is empty for active lane so won't process
            for vehID in vehicleSet:
                try:
                    signal = self.sigCtrl.CAM.receiveData[vehID]['signal']
                    if signal['BLINKER_LEFT']:
                        turnDict['LEFT'] += 1
                    elif signal['BLINKER_RIGHT']:
                        turnDict['RIGHT'] += 1
                    else:
                        turnDict['DIRECT'] += 1
                except:
                    pass # print('No vehID: ', vehID)
            turnCounts.append(turnDict)
        return turnCounts
