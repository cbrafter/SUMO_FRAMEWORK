#!/usr/bin/env python
"""
@file    CDOTS.py
@author  Craig Rafter
@date    19/08/2016

class for ROSA - the Resource Optimised Signal Adaptation algorithm
class for (A)DOTS - Data/Dynamically Optmised Traffic Signals
class for C-DOTS - Connected Data Optmised Traffic Signals
class for AROS - Adaptive Resource Optimised Signals 
class for SCOAR - Signal Control by Optimisation of Available Resources

"""
import signalControl, readJunctionData, traci
import signalTools as sigTools
from math import atan2, degrees, ceil, hypot
import numpy as np
from collections import defaultdict
import traci.constants as tc
from cooperativeAwarenessMessage import CAMChannel
import cdots_utils as cutils


class CDOTS(signalControl.signalControl):
    def __init__(self, junctionData, minGreenTime=10., maxGreenTime=60.,
                 scanRange=250, loopIO=False, CAMoverride=False, model='simpleT',
                 PER=0., noise=False, pedStageActive=False,
                 activationArray=np.ones(7), weightArray=np.ones(7, dtype=float),
                 sync=False, junctions=None, syncFactor=0.0, syncMode='NO'):
        super(CDOTS, self).__init__()
        self.junctionData = junctionData
        self.setTransitionTime(self.junctionData.id)
        self.firstCalled = traci.simulation.getCurrentTime()
        self.lastCalled = self.firstCalled
        self.TIME_MS = self.firstCalled
        self.TIME_SEC = 0.001 * self.TIME_MS
        self.mode = self.getMode()
        self.model = model
        self.currentStageIndex = 0
        if 'selly' not in self.model:
            self.Nstages = len(self.junctionData.stages)
            traci.trafficlights.setRedYellowGreenState(self.junctionData.id, 
                self.junctionData.stages[self.currentStageIndex].controlString)
        else:
            self.Nstages = len(self.junctionData.stages[self.mode])
            traci.trafficlights.setRedYellowGreenState(self.junctionData.id, 
                self.junctionData.stages[self.mode][self.currentStageIndex].controlString)
        self.stageLastCallTime = [0.0]*self.Nstages
        self.stagesSinceLastCall = [0]*self.Nstages
        self.setModelName(model)
        self.scanRange = scanRange
        self.jcnPosition = np.array(traci.junction.getPosition(self.junctionData.id))
        self.jcnCtrlRegion = self.getJncCtrlRegion()
        # self.laneNumDict = sigTools.getLaneNumbers()
        self.controlledLanes = traci.trafficlights.getControlledLanes(self.junctionData.id)
        # dict[laneID] = {heading; float, shape:((x1,y1),(x2,y2))}
        # self.laneDetectionInfo = sigTools.getIncomingLaneInfo(self.controlledLanes)
        self.allLaneInfo = sigTools.getIncomingLaneInfo(traci.lane.getIDList())
        self.edgeLaneMap = sigTools.edgeLaneMap()
        self.stageTime = 0.0
        self.minGreenTime = 2*self.intergreen
        self.maxGreenTime = 10*self.intergreen
        # self.secondsPerMeterTraffic = 0.45
        # self.nearVehicleCatchDistance = 28 # 2sec gap at speed limit 13.89m/s
        self.extendTime = 1.5 # 5 m in 10 m/s (acceptable journey 1.333)
        self.controlledEdges, self.laneInductors = self.getInductorMap()

        self.loopIO = loopIO
        self.threshold = 2.0
        self.activeLanes = self.getActiveLanesDict()

        self.stopCounter = None
        self.emissionCounter = None

        lanes = [x for x in traci.lane.getIDList() if x[0] != ':']
        speedLimDict = {lane: traci.lane.getMaxSpeed(lane) for lane in lanes}
        self.nearVehicleCatchDistanceDict =\
            {lane: 2.0*speedLimDict[lane] for lane in lanes}
        carLen = float(traci.vehicletype.getLength('car') +
                       traci.vehicletype.getMinGap('car'))
        queueMax = 200.0
        # Justification: clear queue if queue length is close to exceeding
        # the control radius of 250 m so 200m<250m. The max green time should 
        # then be set for queues exceeding this 200m threshold
        self.secPerMeterTraffic = self.maxGreenTime/queueMax
        self.secondsPerMeterTrafficDict =\
            {lane: carLen/speedLimDict[lane] for lane in lanes}

        # Pedestrian parameters
        self.pedTime = 1000 * sigTools.getJunctionDiameter(self.junctionData.id)/1.2
        self.pedStage = False
        if 'selly' not in self.model:
            self.pedCtrlString = 'r'*len(self.junctionData.stages[self.currentStageIndex].controlString)
        else:
            self.pedCtrlString = 'r'*len(self.junctionData.stages[self.mode][self.currentStageIndex].controlString)
        self.stagesSinceLastPedStage = 0
        juncsWithPedStages = ['junc0', 'junc1', 'junc4', 
                              'junc5', 'junc6', 'junc7']
        if self.junctionData.id in juncsWithPedStages and pedStageActive:
            self.hasPedStage = True 
        else:
            self.hasPedStage = False

        # Stage calculation utility
        self.sync = sync
        if self.sync:
            self.getSyncDict()
            self.getSyncRelations()
            self.sync = self.junctionData.id in self.syncDict.keys()

        self.stageOptimiser = cutils.stageOptimiser(self,
                                                    activationArray=activationArray,
                                                    weightArray=weightArray,
                                                    sync=self.sync,
                                                    syncFactor=syncFactor,
                                                    syncMode=syncMode)

        # Rolling average stage length
        if 'selly' not in self.model:
            self.stageAvgs = {k.id: [self.maxGreenTime/2.0]*10
                              for k in self.junctionData.stages}   
        else:
            self.stageAvgs = {k.id: [self.maxGreenTime/2.0]*10
                              for k in self.junctionData.stages[self.mode]}
            
        self.stageAvgIndexer = [0]*self.Nstages

        # setup CAM channel
        self.CAM = CAMChannel(self.jcnPosition, self.jcnCtrlRegion,
                              scanRange=self.scanRange,
                              CAMoverride=CAMoverride,
                              PER=PER, noise=noise, CDOTS=True)

        # subscribe to vehicle params
        traci.junction.subscribeContext(self.junctionData.id, 
            tc.CMD_GET_VEHICLE_VARIABLE, 
            self.scanRange, 
            varIDs=(tc.VAR_POSITION, tc.VAR_ANGLE, tc.VAR_SPEED, tc.VAR_TYPE,
                    tc.VAR_SIGNALS, tc.VAR_LANE_ID))

        # only subscribe to loop params if necessary
        if self.loopIO:
            traci.junction.subscribeContext(self.junctionData.id, 
                tc.CMD_GET_INDUCTIONLOOP_VARIABLE, 
                250, 
                varIDs=(tc.LAST_STEP_TIME_SINCE_DETECTION,))

        self.stageData = []

    def process(self, time=None, stopCounter=None, emissionCounter=None):
        self.TIME_MS = time if time is not None else self.getCurrentSUMOtime()
        self.TIME_SEC = 0.001 * self.TIME_MS
        self.stageTime = max(self.minGreenTime, self.stageTime)
        self.stageTime = min(self.stageTime, self.maxGreenTime)
        self.stopCounter = stopCounter
        self.emissionCounter = emissionCounter

        # Packets sent on this step
        # packet delay + only get packets towards the end of the second
        #if (not self.TIME_MS % self.packetRate) and (not 50 < self.TIME_MS % 1000 < 650):
        self.getSubscriptionResults()
        self.CAM.channelUpdate(self.subResults, self.TIME_SEC)
        # else:
        #     self.CAMactive = False

        # Update stage decisions
        # If there's no ITS enabled vehicles present use VA ctrl
        self.numCAVs = len(self.CAM.receiveData)
        isControlInterval = not self.TIME_MS % 1000
        self.elapsedTime = self.getElapsedTime()
        Tremaining = self.stageTime - self.elapsedTime
        if self.pedStage:
            pass  # no calculations needed for ped stage
        elif Tremaining <= 5.0:
            # get loop extend
            try:
                if self.loopIO and self.numCAVs > 0:
                    loopExtend = self.getLoopExtension()
                else:
                    loopExtend = None
            except:
                loopExtend = None

            # get GPS extend
            try:
                if self.numCAVs > 0:
                    gpsExtend = self.getCVextension()
                else:
                    gpsExtend = None
            except:
                gpsExtend = None

            # update stage time
            if loopExtend is not None and gpsExtend is not None:
                updateTime = max(loopExtend, gpsExtend)
            elif loopExtend is not None and gpsExtend is None:
                updateTime = loopExtend
            elif loopExtend is None and gpsExtend is not None:
                updateTime = gpsExtend
            else:
                if 'selly' in self.model:
                    fixedTime = self.junctionData.stages[self.mode][self.currentStageIndex].period
                else:
                    fixedTime = self.junctionData.stages[self.currentStageIndex].period
                updateTime = max(0.0, fixedTime-self.elapsedTime)
            self.updateStageTime(updateTime)
        # If we've just changed stage get the queuing information
        elif self.elapsedTime <= 0.11 and self.numCAVs > 0:
            try:
                queueExtend = self.getQueueExtension()
                self.updateStageTime(queueExtend)
            except:
                pass
            # print(self.junctionData.id, self.stageTime)
        # run GPS extend only to check if queue cancelation needed
        elif self.elapsedTime > self.minGreenTime\
          and np.isclose(self.elapsedTime%2.7, 0., atol=0.05) and self.numCAVs > 0:
            # print('checking')
            gpsExtend = self.getCVextension()
        # process stage as normal
        else:
            pass

        # Stage transition manager
        if self.transitionObject.active:
            pass # If the transition object is active i.e. processing a transition
        elif not self.pedStage  and (self.TIME_MS - self.lastCalled) < self.stageTime*1000:
            pass # Before the period of the next stage
        elif self.pedStage and (self.TIME_MS - self.lastCalled) < self.pedTime:
            pass
        else:
            # Transitioning to next stage
            # record the most recent end time for a stage so we can calculate 
            # how long since the stage was last used
            self.stageLastCallTime[self.currentStageIndex] = self.TIME_SEC
            # Update running average stage time
            self.updateStageAvg(self.elapsedTime)
            # if self.junctionData.id == 'junc3': print(nextStageIndex)
            # Log info about the stages
            if 'selly' in self.model:
                self.stageData.append((self.junctionData.id,
                                       self.junctionData.stages[self.mode][self.currentStageIndex].id,
                                       self.TIME_SEC,
                                       self.elapsedTime))
            else:
                self.stageData.append((self.junctionData.id,
                                       self.junctionData.stages[self.currentStageIndex].id,
                                       self.TIME_SEC,
                                       self.elapsedTime))
            
            # change mode only at this point to avoid changing the stage time
            # mid-process
            self.mode = self.getMode()
            # We have completed one cycle, DO ped stage
            if self.hasPedStage and self.stagesSinceLastPedStage > self.Nstages and not self.pedStage:
                self.pedStage = True
                self.stagesSinceLastPedStage = 0
                if 'selly' in self.model:
                    currentStage = self.junctionData.stages[self.mode][self.currentStageIndex].controlString
                else:
                    currentStage = self.junctionData.stages[self.currentStageIndex].controlString
                nextStage = self.pedCtrlString
            # Completed ped stage, resume signalling
            elif self.hasPedStage and self.pedStage:
                if self.sync:
                    self.stageOptimiser.getSyncVector()
                nextStageIndex = self.stageOptimiser.getNextStageIndex()
                self.pedStage = False
                currentStage = self.pedCtrlString
                if 'selly' in self.model:
                    nextStage = self.junctionData.stages[self.mode][nextStageIndex].controlString
                else:
                    nextStage = self.junctionData.stages[nextStageIndex].controlString
                self.currentStageIndex = nextStageIndex
                self.updateStageCalls()
            # No ped action, normal cycle
            else:
                if self.sync:
                    self.stageOptimiser.getSyncVector()
                nextStageIndex = self.stageOptimiser.getNextStageIndex()
                if 'selly' in self.model:
                    currentStage = self.junctionData.stages[self.mode][self.currentStageIndex].controlString
                    nextStage = self.junctionData.stages[self.mode][nextStageIndex].controlString
                else:
                    currentStage = self.junctionData.stages[self.currentStageIndex].controlString
                    nextStage = self.junctionData.stages[nextStageIndex].controlString
                self.currentStageIndex = nextStageIndex
                self.stagesSinceLastPedStage += 1
                self.updateStageCalls()
            
            self.transitionObject.newTransition(
                self.junctionData.id, currentStage, nextStage)
            self.lastCalled = self.TIME_MS
            self.stageTime = 0.0

        super(CDOTS, self).process(self.TIME_MS)

    def getSubscriptionResults(self):
        self.subResults = traci.junction.getContextSubscriptionResults(self.junctionData.id)

    def updateStageTime(self, updateTime):
        # update time is the seconds to add
        self.elapsedTime = self.getElapsedTime()
        Tremaining = self.stageTime - self.elapsedTime
        self.stageTime = self.elapsedTime + max(updateTime, Tremaining)
        self.stageTime = max(self.minGreenTime, self.stageTime)
        self.stageTime = float(min(self.stageTime, self.maxGreenTime))

    def updateStageCalls(self):
        # Count how many stages have been called since stage last used
        for i in range(self.Nstages):
            if i != self.currentStageIndex:
                self.stagesSinceLastCall[i] += 1
            else:
                self.stagesSinceLastCall[i] = 0

    def cancelQueueExtend(self):
        # cancels queue extend if traffic queue can't move
        self.elapsedTime = self.getElapsedTime()
        if self.elapsedTime >= self.minGreenTime:
            # x = self.stageTime
            self.stageTime = self.elapsedTime
            # print(self.junctionData.id, x, self.stageTime)

    def getElapsedTime(self):
        return 0.001*(self.TIME_MS - self.lastCalled)

    def getJncCtrlRegion(self):
        jncPosition = traci.junction.getPosition(self.junctionData.id)
        otherJuncPos = [traci.junction.getPosition(x)\
                        for x in traci.trafficlights.getIDList()\
                        if x != self.junctionData.id]
        ctrlRegion = {'N':jncPosition[1] + self.scanRange,
                      'S':jncPosition[1] - self.scanRange, 
                      'E':jncPosition[0] + self.scanRange,
                      'W':jncPosition[0] - self.scanRange}

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

                # East/West Boundary
                if abs(dx) < self.scanRange:
                    if dx < -TOL:
                        ctrlRegion['E'] = min(pos[0] - TOL, ctrlRegion['E'])
                    elif dx > TOL:
                        ctrlRegion['W'] = max(pos[0] + TOL, ctrlRegion['W'])

        return ctrlRegion

    def getOncomingVehicles(self, headingTol=15, stageIndexOverride=None):
        # Oncoming if (in active lane & heading matches oncoming heading & 
        # is in lane bounds)
        vehicles = []
        targetLanes = []

        for edges in self.getActiveEdges(stageIndexOverride=stageIndexOverride):
            for edge in self.controlledEdges[edges]:
                targetLanes += self.edgeLaneMap[edge]

        # make set of target lanes for faster lookup
        targetLanes = set(targetLanes)
        for lane in targetLanes:
            laneHeading = self.allLaneInfo[lane]['heading']
            headingUpper = laneHeading + headingTol
            headingLower = laneHeading - headingTol
            for vehID in self.CAM.receiveData.keys():
                vehHeading = self.CAM.receiveData[vehID]['heading']
                vehLane = self.CAM.receiveData[vehID]['lane']
                # If on correct heading +- TOL degrees
                headingCheck = headingLower <= vehHeading <= headingUpper
                # If in vehicle in the targetLane
                laneCheck = vehLane in targetLanes
                if headingCheck and laneCheck:
                    vehicles.append(vehID)

        return sigTools.unique(vehicles)

    def getActiveEdges(self, stageIndexOverride=None):
        return sigTools.lane2edge(self.getActiveLanes(stageIndexOverride=stageIndexOverride))

    def getActiveLanes(self, stageIndexOverride=None):
        # Get the current control string to find the green lights
        if 'selly' in self.model:
            if stageIndexOverride is None:
                stageCtrlString = self.junctionData\
                                      .stages[self.mode][self.currentStageIndex]\
                                      .controlString
            else:
                stageCtrlString = self.junctionData\
                                      .stages[self.mode][stageIndexOverride]\
                                      .controlString
        else:
            if stageIndexOverride is None:
                stageCtrlString = self.junctionData\
                                      .stages[self.currentStageIndex]\
                                      .controlString
            else:
                stageCtrlString = self.junctionData\
                                      .stages[stageIndexOverride]\
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

    def getActiveLanesDict(self):
        # Get the current control string to find the green lights
        activeLanesDict = {}
        if 'selly' in self.model:
            stageInfo = self.junctionData.stages[self.mode]
        else:
            stageInfo = self.junctionData.stages
        for n, stage in enumerate(stageInfo):
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

    def getLaneInductors(self):
        laneInductors = defaultdict(list)

        for loop in traci.inductionloop.getIDList():
            loopLane = traci.inductionloop.getLaneID(loop)
            if loopLane in self.controlledLanes:
                laneInductors[loopLane].append(loop)
            
        return laneInductors

    def getFurthestStationaryVehicle(self, vehIDs):
        furthestID = ''
        maxDistance = -1
        haltVelocity = 0.01 
        for ID in vehIDs:
            vehPosition = np.array(self.CAM.receiveData[ID]['coords'])
            distance = sigTools.getDistance(vehPosition, self.jcnPosition)
            # sumo defines a vehicle as halted if v< 0.01 m/s
            if distance > maxDistance \
              and self.CAM.receiveData[ID]['speed'] < haltVelocity:
                furthestID = ID
                maxDistance = distance

        return [furthestID, maxDistance]

    def getNearestVehicle(self, vehIDs, minDistance=28):
        nearestID = ''
        
        for ID in vehIDs:
            vehPosition = np.array(self.CAM.receiveData[ID]['coords'])
            distance = sigTools.getDistance(vehPosition, self.jcnPosition)
            if distance < minDistance:
                nearestID = ID
                minDistance = distance

        return {'id': nearestID, 'distance': minDistance}

    def getLaneDetectTime(self):
        activeLanes = self.getActiveLanes()
        detectTimePerLane = []
        retrievedEdges = []
        flowConst = tc.LAST_STEP_TIME_SINCE_DETECTION
        edges = sigTools.unique([lane.split('_')[0] for lane in activeLanes])
        for edge in edges:
            detectTimes = []
            for loop in self.laneInductors[edge]:
                detectTimes.append(self.subResults[loop][flowConst])
            detectTimePerLane.append(detectTimes)

        return meanDetectTimePerLane

    def getInductorMap(self):
        otherJunctionLanes = []
        juncIDs = traci.trafficlights.getIDList()
        for junc in juncIDs:
            if junc != self.junctionData.id:
                lanes = self.getLanes(junc)
                otherJunctionLanes += lanes['incoming'] + lanes['outgoing']
        links = self.getLanes(self.junctionData.id)
        self.linkRelation = defaultdict(list)
        ctrlEdges = {}
        routes = sigTools.getRouteDict()[self.modelName]
        for lane in links['incoming']:
            laneHeading = self.allLaneInfo[lane+'_0']['heading']
            lanesBefore = []
            lanesAfter = []
            ctrlLanes = []
            for route in routes:
                try:
                    rIndex = route.index(lane)
                except ValueError:
                    continue

                if rIndex < 1:
                    continue
                # traverse routes but only up to 3 adjacent edges
                for edgeIdx in list(range(rIndex-1, -1, -1))[:3]:
                    if route[edgeIdx] not in otherJunctionLanes:
                        lanesBefore.append(route[edgeIdx])
                        shape = traci.lane.getShape(route[edgeIdx]+'_0')
                        heading = sigTools.getSUMOHeading(shape[-1], shape[0])
                        if laneHeading-20 < heading < laneHeading+20: 
                            ctrlLanes.append(route[edgeIdx])
                    else:
                        break

                if rIndex >= len(route)-1:
                    continue
                for edgeIdx in range(rIndex+1, len(route))[:3]:
                    if route[edgeIdx] not in otherJunctionLanes:
                        lanesAfter.append(route[edgeIdx])
                    else:
                        break

            self.linkRelation[lane] = sigTools.unique(lanesBefore+[lane]+lanesAfter)
            ctrlEdges[lane] = sigTools.unique(ctrlLanes+[lane])

        loopRelation = {}
        loopIDs = traci.inductionloop.getIDList()
        loopLanes = defaultdict(list)
        for loop in loopIDs:
            edge = traci.inductionloop.getLaneID(loop).split('_')[0]
            edgeShapes = traci.lane.getShape(edge+'_0')
            distFromJunc = max([sigTools.getDistance(x, self.jcnPosition)\
                                for x in edgeShapes])
            if distFromJunc < 200:
                loopLanes[edge].append(loop)

        for key in self.linkRelation.keys():
            laneLoops = []
            for lane in self.linkRelation[key]:
                laneLoops += loopLanes[lane]
            loopRelation[key] = laneLoops
        
        if 'selly' in self.modelName:
            loopRelation = self.sellyOakLoops(loopRelation)

        return ctrlEdges, loopRelation

    def getLanes(self, junctionID):
        links = traci.trafficlights.getControlledLinks(junctionID)
        incomingLanes = [x[0][0] for x in links]
        outgoingLanes = [x[0][1] for x in links]
        incomingLanes = [x.split('_')[0] for x in incomingLanes]
        outgoingLanes = [x.split('_')[0] for x in outgoingLanes]
        incomingLanes = sigTools.unique(incomingLanes)
        outgoingLanes = sigTools.unique(outgoingLanes)
        return {'incoming': incomingLanes, 'outgoing': outgoingLanes}

    def getLoopExtension(self):
        detectTimes = sigTools.flatten(self.getLaneDetectTime())
        detectTimes = np.array(detectTimes)
        if not detectTimes.any():
            return None
        # Set adaptive time limit
        try:
            cond1 = np.any(detectTimes <= self.threshold)
            #cond2 = np.std(detectTimes) < 2*self.threshold
            #cond3 = np.mean(detectTimes) < 3*self.threshold
        except Exception as e:
            print(self.getActiveLanes(), detectTimes)
            raise(e)
        if cond1:
            loopExtend = self.extendTime
        else:
            loopExtend = 0.0
        return loopExtend

    def getCVextension(self):
        # If active and on the second, or transition then make stage descision
        oncomingVeh = self.getOncomingVehicles()
        haltVelocity = 0.01
        # If currently staging then extend time if there are vehicles close 
        # to the stop line.
        catchDistance = self.getNearVehicleCatchDistance()
        nearestVeh = self.getNearestVehicle(oncomingVeh, catchDistance)
        
        # nV[1] is its velocity
        # If a vehicle detected and within catch distance
        if (nearestVeh['id'] != '') and (nearestVeh['distance'] <= catchDistance):
            # if not invalid and travelling faster than SPM velocity
            vData = self.CAM.receiveData[nearestVeh['id']]
            if (vData['speed'] > haltVelocity):
                dt = abs(self.TIME_SEC - vData['Tgen'])
                distance = abs(nearestVeh['distance'] - vData['speed']*dt)
                distance = sigTools.ceilRound(distance, 0.1)
                gpsExtend = distance/vData['speed']
                gpsExtend = sigTools.ceilRound(distance/vData['speed'], 0.1)

                # 2 second typical time headway between vehicles, HEOMM journey
                # is unreliable if greater than 1.67 free flow. 2*1.67 = 3.34s
                # taking the ceiling value of this threshold we get 4s.
                if gpsExtend > 2*self.threshold:
                    gpsExtend = 0.0
            else:
                # light green but queue not moving
                self.cancelQueueExtend()
                gpsExtend = 0.0
        # no detectable vehicle near
        else:
            # gpsExtend = None
            gpsExtend = 0.0
        return gpsExtend

    def getQueueLength(self):
        oncomingVeh = self.getOncomingVehicles()
        # If new stage get furthest from stop line whose velocity < 5% speed
        # limit and determine queue length
        queueInfo = self.getFurthestStationaryVehicle(oncomingVeh)
        return queueInfo  # [vehID, distance]

    def getQueueExtension(self):
        queueInfo = self.getQueueLength()
        # secondsPerMeterTraffic = self.getSecondsPerMeterTraffic()
        # secondsPerMeterTraffic = 0.3  # reach max green by 200m
        if queueInfo != '':
            queueExtend = ceil(self.secPerMeterTraffic*queueInfo[1])
        # If we're in this state this should never happen but just in case
        else:
            queueExtend = 0.0
        return queueExtend

    def getSecondsPerMeterTraffic(self):
        activeLanes = self.getActiveLanes()
        spmts = [self.secondsPerMeterTrafficDict[lane] for lane in activeLanes]
        return max(spmts)

    def getNearVehicleCatchDistance(self):
        activeLanes = self.getActiveLanes()
        nvcd = [self.nearVehicleCatchDistanceDict[lane] for lane in activeLanes]
        return max(nvcd)

    def sellyOakLoops(self, loopRelation):
        if self.junctionData.id == 'junc10':
            loopRelation['edge199'] = ['42', '43', '44', '54',
                                       '55', '36', '37', '38']
        elif self.junctionData.id == 'junc11':
            loopRelation['edge281'] = ['38']
        elif self.junctionData.id == 'junc12':
            loopRelation['edge3177'] = ['6', '5']
            loopRelation['edge3176'] = ['7', '8']
            loopRelation['edge3174'] = ['7', '8']
        elif self.junctionData.id == 'junc3':
            loopRelation['edge3172'] = ['10', '9']
            loopRelation['edge3171'] = ['62', '0', '15', '16','10', '9'] 
            loopRelation['edge142'] = ['15', '16', '10', '9', '1', '2'] 
            loopRelation['edge46'] = ['15', '16', '11', '12']
        elif self.junctionData.id == 'junc6':
            loopRelation['edge131'] = ['23', '24']
        elif self.junctionData.id == 'junc7':
            loopRelation['edge113'] = ['6', '5']
        elif self.junctionData.id == 'junc8':
            loopRelation['edge116'] = ['3', '4']
            loopRelation['edge117'] = ['3', '4']
        elif self.junctionData.id == 'junc9':
            loopRelation['edge211'] = ['29', '30', '39', '40', '41']
        else:
            pass

        return loopRelation

    def getMode(self):
        timeOfDay = self.TIME_SEC % 86400  # modulo 1 day in seconds for spill over
        # 00:00 - 06:00
        if 0 <= timeOfDay < 21600:
            return 'OFF'
        # 06:00 - 11:00    
        elif 21600 <= timeOfDay < 39600:
            return 'PEAK'
        # 11:00 - 16:00
        elif 39600 <= timeOfDay < 57600:
            return 'INTER'
        # 16:00 - 20:00
        elif 57600 <= timeOfDay < 72000:
            return 'PEAK'
        # 20:00 - 00:00
        elif 72000 <= timeOfDay < 86400:
            return 'OFF'
        else:
            return 'INTER'

    def getSyncDict(self):
        self.syncDict = defaultdict(list)
        self.syncDict['junc3'] = ['junc12']
        self.syncDict['junc12'] = ['junc3']
        self.syncDict['junc7'] = ['junc8']
        self.syncDict['junc8'] = ['junc7']
        self.syncDict['junc4'] = ['junc5']
        self.syncDict['junc5'] = ['junc4', 'junc6']
        self.syncDict['junc6'] = ['junc5']
        #self.syncDict['junc9'] = ['junc10', junc11'] # only has two stages
        self.syncDict['junc10'] = ['junc11']

    def setSyncJunctions(self, junctions):
        self.syncJuncs = {}
        for j in junctions:
            if j.junctionData.id in self.syncDict[self.junctionData.id]:
                self.syncJuncs[j.junctionData.id] = j

    def getSyncRelations(self):
        # Stages from coordinating junction the stage at this junction
        # receives from
        # Format: <JUNCTIONID>_<STAGEID>_<DIRECTION>
        self.syncRels = {}
        # JUNCTION 3
        if self.junctionData.id == 'junc3':
            self.syncRels['junc3_0'] = ['junc12_0_D', 'junc12_1_R', 'junc12_3_L']
            self.syncRels['junc3_1'] = []
            self.syncRels['junc3_2'] = []
            self.syncRels['junc3_3'] = []
        # JUNCTION 12
        elif self.junctionData.id == 'junc12':
            self.syncRels['junc12_0'] = []
            self.syncRels['junc12_1'] = []
            self.syncRels['junc12_2'] = ['junc3_2_D','junc3_1_L', 'junc3_3_R']
            self.syncRels['junc12_3'] = []
        # JUNCTION 7
        elif self.junctionData.id == 'junc7':
            self.syncRels['junc7_0'] = []
            self.syncRels['junc7_1'] = ['junc8_0_D', 'junc8_2_L']
            self.syncRels['junc7_2'] = []
        # JUNCTION 8
        elif self.junctionData.id == 'junc8':
            self.syncRels['junc8_0'] = []
            self.syncRels['junc8_1'] = ['junc7_1_D', 'junc7_2_L']
            self.syncRels['junc8_2'] = []
        # JUNCTION 4
        elif self.junctionData.id == 'junc4':
            self.syncRels['junc4_0'] = ['junc5_0_D', 'junc5_1_R', 'junc5_3_L']
            self.syncRels['junc4_1'] = []
            self.syncRels['junc4_2'] = []
        # JUNCTION 5
        elif self.junctionData.id == 'junc5':
            self.syncRels['junc5_0'] = []
            self.syncRels['junc5_1'] = []
            self.syncRels['junc5_2'] = ['junc4_1_D', 'junc6_1_D', 'junc4_2_R', 'junc6_2_R']
            self.syncRels['junc5_3'] = []
        # JUNCTION 6
        elif self.junctionData.id == 'junc6':
            self.syncRels['junc6_0'] = ['junc5_2_D', 'junc5_1_L', 'junc5_3_R']
            self.syncRels['junc6_1'] = []
            self.syncRels['junc6_2'] = []
        # JUNCTION 9
        # elif self.junctionData.id == 'junc9':
        #     self.syncRels['junc'] = ['junc']
        # JUNCTION 10
        elif self.junctionData.id == 'junc10':
            self.syncRels['junc10_0'] = []
            self.syncRels['junc10_1'] = ['junc11_0_D']
            self.syncRels['junc10_2'] = []
            self.syncRels['junc10_3'] = []
        else:
            pass

    def getID(self):
        return self.junctionData.id

    def getStageID(self):
        if 'selly' in self.model:
            return self.junctionData.stages[self.mode][self.currentStageIndex].id
        else:
            return self.junctionData.stages[self.currentStageIndex].id

    def getSyncString(self):
        return self.getID() + '_' + self.getStageID()

    def getAvgStageTime(self):
        means = [0.0]*self.Nstages
        for stageID in self.stageAvgs.keys():
            means[int(stageID)] = sigTools.mean(self.stageAvgs[stageID])
        return means

    def updateStageAvg(self, time):
        stageID = self.getStageID()
        intID = int(stageID)
        self.stageAvgs[stageID][self.stageAvgIndexer[intID]] = time
        self.stageAvgIndexer[intID] += 1
        self.stageAvgIndexer[intID] %= 10

