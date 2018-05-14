#!/usr/bin/env python
"""
@file    HybridVAControl.py
@author  Craig Rafter
@date    19/08/2016

class for fixed time signal control

"""
import signalControl, readJunctionData, traci
import signalTools as sigTools
from math import atan2, degrees, ceil, hypot
import numpy as np
from collections import defaultdict
import traci.constants as tc
from cooperativeAwarenessMessage import CAMChannel

class HybridVAControl(signalControl.signalControl):
    def __init__(self, junctionData, minGreenTime=10., maxGreenTime=60.,
                 scanRange=250, loopIO=False, CAMoverride=False):
        super(HybridVAControl, self).__init__()
        self.junctionData = junctionData
        self.Nstages = len(self.junctionData.stages)
        self.firstCalled = traci.simulation.getCurrentTime()
        self.lastCalled = self.firstCalled
        self.lastStageIndex = 0
        traci.trafficlights.setRedYellowGreenState(self.junctionData.id, 
            self.junctionData.stages[self.lastStageIndex].controlString)
        
        self.scanRange = scanRange
        self.jcnPosition = np.array(traci.junction.getPosition(self.junctionData.id))
        self.jcnCtrlRegion = self._getJncCtrlRegion()
        self.controlledLanes = traci.trafficlights.getControlledLanes(self.junctionData.id)
        # dict[laneID] = [heading, shape]
        self.laneDetectionInfo = sigTools.getIncomingLaneInfo(self.controlledLanes)
        self.stageTime = 0.0
        self.minGreenTime = minGreenTime
        self.maxGreenTime = maxGreenTime
        self.secondsPerMeterTraffic = 0.45
        self.nearVehicleCatchDistance = 28 # 2sec gap at speed limit 13.89m/s
        self.extendTime = 1.0 # 5 m in 10 m/s (acceptable journey 1.333)
        self.laneInductors = self._getLaneInductors()

        self.TIME_MS = self.firstCalled
        self.TIME_SEC = 0.001 * self.TIME_MS
        self.lastStepCatch = 2
        self.loopIO = loopIO
        self.threshold = 2.5
        self.activeLanes = self._getActiveLanesDict()
        # self.speedLims = sigTools.speedLimDict()
        # self.vTypeIndex = sigTools.vTypeDict()

        # setup CAM channel
        self.CAM = CAMChannel(self.jcnPosition, self.jcnCtrlRegion,
                              self.scanRange, CAMoverride)

        # subscribe to vehicle params
        traci.junction.subscribeContext(self.junctionData.id, 
            tc.CMD_GET_VEHICLE_VARIABLE, 
            self.scanRange, 
            varIDs=(tc.VAR_POSITION, tc.VAR_ANGLE, tc.VAR_SPEED, tc.VAR_TYPE))

        # only subscribe to loop params if necessary
        if self.loopIO:
            traci.junction.subscribeContext(self.junctionData.id, 
                tc.CMD_GET_INDUCTIONLOOP_VARIABLE, 
                50, 
                varIDs=(tc.LAST_STEP_TIME_SINCE_DETECTION,))


    def process(self):
        self.TIME_MS = self.getCurrentSUMOtime()
        self.TIME_SEC = 0.001 * self.TIME_MS
        self.stageTime = max(self.minGreenTime, self.stageTime)
        self.stageTime = min(self.stageTime, self.maxGreenTime)
        # Packets sent on this step
        # packet delay + only get packets towards the end of the second
        #if (not self.TIME_MS % self.packetRate) and (not 50 < self.TIME_MS % 1000 < 650):
        self._getSubscriptionResults()
        self.CAM.channelUpdate(self.subResults, self.TIME_SEC)
        # else:
        #     self.CAMactive = False

        # Update stage decisions
        # If there's no ITS enabled vehicles present use VA ctrl
        numCAVs = len(self.CAM.receiveData)
        isControlInterval = not self.TIME_MS % 1000
        elapsedTime = 0.001*(self.TIME_MS - self.lastCalled)
        Tremaining = self.stageTime - elapsedTime
        #if self.junctionData.id == 'b2': print elapsedTime
        if Tremaining < 1:
            # get loop extend
            if self.loopIO:
                detectTimePerLane = self._getLaneDetectTime()
                # Set adaptive time limit
                if np.any(detectTimePerLane < self.threshold):
                    loopExtend = self.extendTime
                else:
                    loopExtend = 0.0
            else:
                loopExtend = 0.0

            # get GPS extend
            if numCAVs > 0:
                # If active and on the second, or transition then make stage descision
                oncomingVeh = self._getOncomingVehicles()
                # If currently staging then extend time if there are vehicles close 
                # to the stop line
                nearestVeh = self._getNearestVehicle(oncomingVeh)
                # nV[1] is its velocity
                # If a vehicle detected and within catch distance
                if nearestVeh['id'] != '' and nearestVeh['distance'] <= self.nearVehicleCatchDistance:
                    # if not invalid and travelling faster than SPM velocity
                    if (self.CAM.receiveData[nearestVeh['id']]['v'] > 1.0/self.secondsPerMeterTraffic):
                        gpsExtend = nearestVeh['distance']/self.CAM.receiveData[nearestVeh['id']]['v']
                    else:
                        gpsExtend = self.secondsPerMeterTraffic*nearestVeh['distance']

                    if gpsExtend > 2*self.threshold:
                        gpsExtend = 0.0
                # no detectable near vehicle
                else:
                    gpsExtend = 0.0
            else:
                gpsExtend = 0.0

            # update stage time
            updateTime = max(loopExtend, gpsExtend)
            self.updateStageTime(updateTime)
        # If we've just changed stage get the queuing information
        elif elapsedTime <= 0.1 and numCAVs > 0:
            oncomingVeh = self._getOncomingVehicles()
            # If new stage get furthest from stop line whose velocity < 5% speed
            # limit and determine queue length
            furthestVeh = self._getFurthestStationaryVehicle(oncomingVeh)
            if furthestVeh[0] != '':
                gpsExtend = self.secondsPerMeterTraffic*furthestVeh[1]
                #if self.junctionData.id == 'b2': print('{}: gpsExtend: {}'.format(self.junctionData.id, gpsExtend))
            # If we're in this state this should never happen but just in case
            else:
                gpsExtend = 0.0

            self.updateStageTime(gpsExtend)
        # process stage as normal
        else:
            pass

        # print(self.stageTime)
        #if isControlInterval:
        if self.transitionObject.active:
            # If the transition object is active i.e. processing a transition
            pass
        elif (self.TIME_MS - self.lastCalled) < self.stageTime*1000:
            # Before the period of the next stage
            pass
        else:
            # Not active, not in offset, stage not finished
            nextStageIndex = (self.lastStageIndex + 1) % self.Nstages
            self.transitionObject.newTransition(
                self.junctionData.id, 
                self.junctionData.stages[self.lastStageIndex].controlString,
                self.junctionData.stages[nextStageIndex].controlString, 
                self.TIME_MS)
            self.lastStageIndex = nextStageIndex
            # print(self.stageTime)
            self.lastCalled = self.TIME_MS
            self.stageTime = 0.0

        super(HybridVAControl, self).process(self.TIME_MS)

    def _getSubscriptionResults(self):
        self.subResults = traci.junction.getContextSubscriptionResults(self.junctionData.id)

    def updateStageTime(self, updateTime):
        elapsedTime = 0.001*(self.TIME_MS - self.lastCalled)
        Tremaining = self.stageTime - elapsedTime
        self.stageTime = elapsedTime + max(updateTime, Tremaining)
        self.stageTime = max(self.minGreenTime, self.stageTime)
        self.stageTime = min(self.stageTime, self.maxGreenTime) 

    def _getJncCtrlRegion(self):
        jncPosition = traci.junction.getPosition(self.junctionData.id)
        otherJuncPos = [traci.junction.getPosition(x) for x in traci.trafficlights.getIDList() if x != self.junctionData.id]
        ctrlRegion = {'N':jncPosition[1]+self.scanRange, 'S':jncPosition[1]-self.scanRange, 
            'E':jncPosition[0]+self.scanRange, 'W':jncPosition[0]-self.scanRange}

        TOL = 10 # Exclusion region around junction boundary
        if otherJuncPos != []:
            for pos in otherJuncPos:
                dx = jncPosition[0] - pos[0]
                dy = jncPosition[1] - pos[1]
                # North/South Boundary
                if abs(dy) < self.scanRange:
                    if dy < -TOL:
                        ctrlRegion['N'] = min(pos[1] - TOL, ctrlRegion['N'])
                    elif dy > TOL:
                        ctrlRegion['S'] = max(pos[1] + TOL, ctrlRegion['S'])
                    else:
                        pass
                else:
                    pass

                # East/West Boundary
                if abs(dx) < self.scanRange:
                    if dx < -TOL:
                        ctrlRegion['E'] = min(pos[0] - TOL, ctrlRegion['E'])
                    elif dx > TOL:
                        ctrlRegion['W'] = max(pos[0] + TOL, ctrlRegion['W'])
                    else:
                        pass
                else:
                    pass

        return ctrlRegion

    def _getOncomingVehicles(self, headingTol=10):
        # Oncoming if (in active lane & heading matches oncoming heading & 
        # is in lane bounds)
        vehicles = []
        for lane in self.activeLanes[self.lastStageIndex]:
            laneHeading = self.laneDetectionInfo[lane]['heading']
            headingUpper = laneHeading + headingTol
            headingLower = laneHeading - headingTol
            laneBounds = self.laneDetectionInfo[lane]['bounds']
            lowerXBound = min(laneBounds['x1'], laneBounds['x2'])
            lowerYBound = min(laneBounds['y1'], laneBounds['y2'])
            upperXBound = max(laneBounds['x1'], laneBounds['x2'])
            upperYBound = max(laneBounds['y1'], laneBounds['y2'])
            for vehID in self.CAM.receiveData.keys():
                vehicleXcoord = self.CAM.receiveData[vehID]['pos'][0]
                vehicleYcoord = self.CAM.receiveData[vehID]['pos'][1]
                # If on correct heading pm 10deg
                if (headingLower < laneHeading < headingUpper
                  # If in lane x bounds
                  and lowerXBound < vehicleXcoord < upperXBound
                  # If in lane y bounds
                  and lowerYBound < vehicleYcoord < upperYBound):
                  # Then append vehicle
                    vehicles.append(vehID)

        vehicles = sigTools.unique(vehicles)
        return vehicles


    def _getActiveLanes(self):
        # Get the current control string to find the green lights
        stageCtrlString = self.junctionData\
                              .stages[self.lastStageIndex]\
                              .controlString
        try:
            # search dict to see if stage known already, if not work it out
            activeLanes = self.activeLanes[stageCtrlString]
        except KeyError:
            activeLanes = self.getLanesFromString(stageCtrlString)
            self.activeLanes[stageCtrlString] = activeLanes
        # Get a list of the unique active lanes
        # activeLanes = sigTools.unique(activeLanes)
        return activeLanes


    def _getActiveLanesDict(self):
        # Get the current control string to find the green lights
        activeLanesDict = {}
        for n, stage in enumerate(self.junctionData.stages):
            activeLanes = self.getLanesFromString(stage.controlString)
            # Get a list of the unique active lanes
            # activeLanes = sigTools.unique(activeLanes)
            activeLanesDict[n] = activeLanes
            activeLanesDict[stage.controlString] = activeLanes
        return activeLanesDict

    def getLanesFromString(self, ctrlString):
        activeLanes = []
        for i, letter in enumerate(ctrlString):
            if letter == 'G' and self.controlledLanes[i] not in activeLanes:
                activeLanes.append(self.controlledLanes[i])
        return activeLanes

    def _getLaneInductors(self):
        laneInductors = defaultdict(list)

        for loop in traci.inductionloop.getIDList():
            loopLane = traci.inductionloop.getLaneID(loop)
            if loopLane in self.controlledLanes:
                laneInductors[loopLane].append(loop)
            
        return laneInductors

    def _getFurthestStationaryVehicle(self, vehIDs):
        furthestID = ''
        maxDistance = -1
        haltVelocity = 0.01 
        for ID in vehIDs:
            vehPosition = np.array(self.CAM.receiveData[ID]['pos'])
            distance = hypot(*(vehPosition - self.jcnPosition))
            # sumo defines a vehicle as halted if v< 0.01 m/s
            if distance > maxDistance \
              and self.CAM.receiveData[ID]['v'] < haltVelocity:
                furthestID = ID
                maxDistance = distance

        return [furthestID, maxDistance]

    def _getNearestVehicle(self, vehIDs):
        nearestID = ''
        minDistance = self.nearVehicleCatchDistance
        
        for ID in vehIDs:
            vehPosition = np.array(self.CAM.receiveData[ID]['pos'])
            distance = hypot(*(vehPosition - self.jcnPosition))
            if distance < minDistance:
                nearestID = ID
                minDistance = distance

        return {'id': nearestID, 'distance': minDistance}

    def _getLaneDetectTime(self):
        activeLanes = self._getActiveLanes()
        meanDetectTimePerLane = np.zeros(len(activeLanes))
        for i, lane in enumerate(activeLanes):
            detectTimes = []
            for loop in self.laneInductors[lane]:
                # if self.subResults != None and self.subResults[loop] != None:
                    #print(traci.inductionloop.getTimeSinceDetection(loop))
                detectTimes.append(self.subResults[loop][tc.LAST_STEP_TIME_SINCE_DETECTION])
            meanDetectTimePerLane[i] = self.mean(detectTimes)

        return meanDetectTimePerLane

    def getInductors(self):
        links = traci.trafficlights.getControlledLinks(self.junctionData.id)
        self.incomingLanes = [x[0][0] for x in links]
        self.outgoingLanes = [x[0][1] for x in links]
        self.incomingLanes = [x.split('_')[0] for x in self.incomingLanes]
        self.outgoingLanes = [x.split('_')[0] for x in self.outgoingLanes]
        self.incomingLanes = sigTools.unique(self.incomingLanes)
        self.outgoingLanes = sigTools.unique(self.outgoingLanes)
