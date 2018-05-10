#!/usr/bin/env python
"""
@file    HybridVAControl.py
@author  Craig Rafter
@date    19/08/2016

class for fixed time signal control

"""
import signalControl, readJunctionData, traci
from math import atan2, degrees, ceil, hypot
import numpy as np
from collections import defaultdict
import traci.constants as tc

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
        self.laneDetectionInfo = self._getIncomingLaneInfo()
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
        self.speedLims = speedLimDict()
        self.vTypeIndex = vTypeDict()

        # CAM Params from ETSI standard
        self.TGenCamMin = 0.1 # Min time for CAM generation 10Hz/100ms/0.1sec
        self.TGenCamMax = 1.0 # Max time for CAM generation 1Hz/1000ms/1sec
        self.TGenCamDCC = 0.1 # CAM generation time under channel congestion
        self.TGenCam = self.TGenCamMax # current upper lim for CAM generation
        self.NGenCamMax = 3
        self.Nsubcarriers = 52 # Num of 802.11p subcarriers
        # Adapt CAM generation based on channel state from ETSI CAM DP2 mode
        self.DCCstate = {'RELAXED':  CAMoverride if CAMoverride else self.TGenCamMin,
                         'ACTIVE': CAMoverride if CAMoverride else 0.2,
                         'RESRICTIVE':  CAMoverride if CAMoverride else 0.25}
        # linear function for active = lambda x: round(numCAVs*0.0155-0.612, 1)
        # for linear increase in DDC time from 0.9*Nsubcarriers and 3*Nsubcarriers
        # dict[vehID] = [position (x), heading(h), velocity(v), TGenCam(TGC), NGenCam (NGC)]
        # where TGenCam is the time the CAM was generated
        self.CamGenData = {} # CAM generated at vehicle T=0
        self.CamChannelData = {} # CAM info in transit T=0.1
        self.CamRxData = {} # CAM info at Junction receiver T=0.2

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
        self._getCAMinfo()
        # else:
        #     self.CAMactive = False

        # Update stage decisions
        # If there's no ITS enabled vehicles present use VA ctrl
        numCAVs = len(self.CamRxData)
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
                if nearestVeh[0] != '' and nearestVeh[1] <= self.nearVehicleCatchDistance:
                    # if not invalid and travelling faster than SPM velocity
                    if (self.CamRxData[nearestVeh[0]]['v'] > 1.0/self.secondsPerMeterTraffic):
                        gpsExtend = nearestVeh[1]/self.CamRxData[nearestVeh[0]]['v']
                    else:
                        gpsExtend = self.secondsPerMeterTraffic*nearestVeh[1]

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
        # elif (self.TIME_MS - self.firstCalled) < (self.junctionData.offset*1000):
        #     # Process offset first
        #     pass
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
            #print(self.stageTime)
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


    def _getHeading(self, currentLoc, prevLoc):
        dy = currentLoc[1] - prevLoc[1]
        dx = currentLoc[0] - prevLoc[0]
        if currentLoc[1] == prevLoc[1] and currentLoc[0] == prevLoc[0]:
            heading = -1
        else:
            if dy >= 0:
                heading = degrees(atan2(dy, dx))
            else:
                heading = 360 + degrees(atan2(dy, dx))
        
        # Map angle to make compatible with SUMO heading
        if 0 <= heading <= 90:
            heading = 90 - heading
        elif 90 < heading < 360:
            heading = 450 - heading

        return heading


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


    def _isInRange(self, vehPosition):
        distance = hypot(*(vehPosition - self.jcnPosition))
        if (distance < self.scanRange 
            and self.jcnCtrlRegion['W'] <= vehPosition[0] <= self.jcnCtrlRegion['E']
            and self.jcnCtrlRegion['S'] <= vehPosition[1] <= self.jcnCtrlRegion['N']):
            return True
        else:
            return False


    # def _getVelocity(self, vehID, vehPosition, Tdetect):
    #     if vehID in self.CamRxData.keys():
    #         oldX = np.array(self.CamRxData[vehID]['pos'])
    #         newX = np.array(vehPosition)

    #         dx = hypot(*(newX - oldX))
    #         dt = Tdetect - self.CamRxData[vehID][3]
    #         velocity = dx/dt

    #         return velocity
    #     else:
    #         return 1e6


    def _getCAMinfo(self):
        # Get data off "channel"
        self.CamRxData = self.CamChannelData.copy()
        
        # Set DCC time based on channel state
        numCAVs = len(self.CamRxData)
        if numCAVs <= 0.75*self.Nsubcarriers:
            self.TGenCamDCC = self.DCCstate['RELAXED']
        elif numCAVs >= 1.5*self.Nsubcarriers:
            self.TGenCamDCC = self.DCCstate['RESRICTIVE']
        else:
            self.TGenCamDCC = self.DCCstate['ACTIVE']

        # Put the last CAMs on the channel
        self.CamChannelData = {}
        GenKeys = self.CamGenData.keys()
        RxKeys = self.CamRxData.keys()
        for vehID in GenKeys:
            if vehID in RxKeys:
                x1, y1 = self.CamRxData[vehID]['pos']
                x2, y2 = self.CamGenData[vehID]['pos']
                dx = hypot(x1-x2, y1-y2)
                dh = abs(self.CamRxData[vehID]['h'] - self.CamGenData[vehID]['h'])
                dv = abs(self.CamRxData[vehID]['v'] - self.CamGenData[vehID]['v'])
                dt = self.TIME_SEC - self.CamRxData[vehID]['Tgen']
                TGC = self._TGC(self.CamRxData[vehID])
            # No data for this vehicle received yet, force trigger onto channel
            else:
                dx = 5
                dh = 5
                dv = 1
                dt = self.TGenCamMax + self.TGenCamMin
                TGC = self.TGenCamMax + self.TGenCamMin
            
            # CAM trigger condition 1 data to channel, NGC=0
            # change in: Position change > 4m, heading > 4deg, or speed > 0.5m/s
            if (dx > 4 or dh > 4 or dv > 0.5) and dt >= self.TGenCamDCC:
                self.CamChannelData[vehID] = self.CamGenData[vehID].copy()
                self.CamChannelData[vehID]['NGC'] = 0
                #if vehID == '8': print('C1')
            # CAM trigger condition 2 - data to channel, NGC++
            elif dt >= self.TGenCamDCC or dt >= TGC:
                self.CamChannelData[vehID] = self.CamGenData[vehID].copy()
                self.CamChannelData[vehID]['NGC'] += 1
                #if vehID == '8': print('C2', self.CamChannelData[vehID]['NGC'], dt, TGC)
            # No change in CAM information, same as what was previously on channel
            else:
                self.CamChannelData[vehID] = self.CamRxData[vehID].copy()
                #if vehID == '8': print('NOCH')
                

        # Get new data for the vehicles
        self.CamGenData = {}
        compareKeys = self.CamChannelData.keys()
        # check subscription has data
        if self.subResults != None:
            for vehID in self.subResults.keys():
                # check the sub result has vehicle data (not loop data)
                if tc.VAR_POSITION in self.subResults[vehID].keys():
                    vehPosition = self.subResults[vehID][tc.VAR_POSITION]
                    if 'c_' in self.subResults[vehID][tc.VAR_TYPE] and self._isInRange(vehPosition):
                        vehHeading = self.subResults[vehID][tc.VAR_ANGLE]
                        vehVelocity = self.subResults[vehID][tc.VAR_SPEED]
                        if vehID in compareKeys:
                            nextNGC = self.CamChannelData[vehID]['NGC']
                            self.CamGenData[vehID] = {'pos': vehPosition,
                                                      'h': vehHeading,
                                                      'v': vehVelocity,
                                                      'Tgen': self.TIME_SEC,
                                                      'NGC': nextNGC}
                        else:
                            self.CamGenData[vehID] = {'pos': vehPosition,
                                                      'h': vehHeading,
                                                      'v': vehVelocity,
                                                      'Tgen': self.TIME_SEC,
                                                      'NGC': 0}


    def _TGC(self, vData):
        if vData['NGC'] > self.NGenCamMax:
            return self.TGenCamMax
        else:
            return self.TIME_SEC - vData['Tgen']


    def _getIncomingLaneInfo(self):
        laneInfo = defaultdict(list) 
        for lane in self.unique(self.controlledLanes):
            shape = traci.lane.getShape(lane)
            width = traci.lane.getWidth(lane)
            heading = self._getHeading(shape[1], shape[0])

            dx = shape[0][0] - shape[1][0] 
            dy = shape[0][1] - shape[1][1]
            if abs(dx) > abs(dy):
                roadBounds = ((shape[0][0], shape[0][1] + width), (shape[1][0], shape[1][1] - width))
            else: 
                roadBounds = ((shape[0][0] + width, shape[0][1]), (shape[1][0] - width, shape[1][1]))
            laneInfo[lane] = [heading, roadBounds]

        return laneInfo


    def _getOncomingVehicles(self):
        # Oncoming if (in active lane & heading matches oncoming heading & 
        # is in lane bounds)
        vehicles = []
        for lane in self.activeLanes[self.lastStageIndex]:
            for vehID in self.CamRxData.keys():
                # If on correct heading pm 10deg
                if (np.isclose(self.CamRxData[vehID]['h'], self.laneDetectionInfo[lane][0], atol=10)
                    # If in lane x bounds
                    and min(self.laneDetectionInfo[lane][1][0][0], self.laneDetectionInfo[lane][1][1][0]) < 
                    self.CamRxData[vehID]['pos'][0] < 
                    max(self.laneDetectionInfo[lane][1][0][0], self.laneDetectionInfo[lane][1][1][0])
                    # If in lane y bounds
                    and min(self.laneDetectionInfo[lane][1][0][1], self.laneDetectionInfo[lane][1][1][1]) < 
                    self.CamRxData[vehID]['pos'][1] < 
                    max(self.laneDetectionInfo[lane][1][0][1], self.laneDetectionInfo[lane][1][1][1])):
                    # Then append vehicle
                    vehicles.append(vehID)

        vehicles = self.unique(vehicles)
        return vehicles


    def _getActiveLanes(self):
        # Get the current control string to find the green lights
        stageCtrlString = self.junctionData.stages[self.lastStageIndex].controlString
        activeLanes = []
        for i, letter in enumerate(stageCtrlString):
            if letter == 'G':
                activeLanes.append(self.controlledLanes[i])
        # Get a list of the unique active lanes
        activeLanes = self.unique(activeLanes)
        return activeLanes


    def _getActiveLanesDict(self):
        # Get the current control string to find the green lights
        activeLanesDict = {}
        for n, stage in enumerate(self.junctionData.stages):
            activeLanes = []
            for i, letter in enumerate(stage.controlString):
                if letter == 'G':
                    activeLanes.append(self.controlledLanes[i])
            # Get a list of the unique active lanes
            activeLanes = self.unique(activeLanes)
            activeLanesDict[n] = activeLanes
        return activeLanesDict


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
        speedLimit = self.speedLims[self.activeLanes[self.lastStageIndex][0]]
        for ID in vehIDs:
            vehPosition = np.array(self.CamRxData[ID]['pos'])
            distance = hypot(*(vehPosition - self.jcnPosition))
            if distance > maxDistance and self.CamRxData[ID]['v'] < 0.05*speedLimit:
                furthestID = ID
                maxDistance = distance

        return [furthestID, maxDistance]


    def _getNearestVehicle(self, vehIDs):
        nearestID = ''
        minDistance = self.nearVehicleCatchDistance + 1
        
        for ID in vehIDs:
            vehPosition = np.array(self.CamRxData[ID]['pos'])
            distance = hypot(*(vehPosition - self.jcnPosition))
            if distance < minDistance:
                nearestID = ID
                minDistance = distance

        return [nearestID, minDistance]


    def _getLaneDetectTime(self):
        activeLanes = self._getActiveLanes()
        meanDetectTimePerLane = np.zeros(len(activeLanes))
        for i, lane in enumerate(activeLanes):
            detectTimes = []
            for loop in self.laneInductors[lane]:
                # if self.subResults != None and self.subResults[loop] != None:
                    #print(traci.inductionloop.getTimeSinceDetection(loop))
                detectTimes.append(self.subResults[loop][tc.LAST_STEP_TIME_SINCE_DETECTION])
            meanDetectTimePerLane[i] = np.mean(detectTimes)

        return meanDetectTimePerLane

    def unique(self, sequence):
        return list(set(sequence))

    def getInductors(self):
        links = traci.trafficlights.getControlledLinks(self.junctionData.id)
        self.incomingLanes = [x[0][0] for x in links]
        self.outgoingLanes = [x[0][1] for x in links]
        self.incomingLanes = [x.split('_')[0] for x in self.incomingLanes]
        self.outgoingLanes = [x.split('_')[0] for x in self.outgoingLanes]
        self.incomingLanes = self.unique(self.incomingLanes)
        self.outgoingLanes = self.unique(self.outgoingLanes)

        
# default dict that finds and remembers road speed limits (only if static)
# needs to be updated otherwise
class speedLimDict(defaultdict):
    def __missing__(self, key):
        self[key] = traci.lane.getMaxSpeed(key)
        return self[key]

# defaultdict that finds and remembers vehicle types (only if static)
# needs to be updated otherwise
class vTypeDict(defaultdict):
    def __missing__(self, key):
        self[key] = traci.vehicle.getTypeID(key)
        return self[key]

# # default dict that collects subsciptions for each vehicle in the network
# class vehSubDict(defaultdict):
#     def __missing__(self, key):

#         self[key] = traci.vehicle.subcribe(key, varIDs=(tc.VAR_POSITION, tc.VAR_ANGLE, tc.VAR_SPEED))
