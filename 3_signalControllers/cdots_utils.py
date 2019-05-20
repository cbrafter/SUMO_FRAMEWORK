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

class costGenerator():
    def __init__(self, signalObj):
        self.signalObj = signalObj

    def getLaneCosts(self):
        pass

    def getQueueLength(self):
        pass

    def getQueueDuration(self):
        pass

    def getTotalWaitingTime(self):
        pass

    def getStops(self):
        pass

    def getSpeedCost(self):
        pass

    def getAccelCost(self):
        pass

    def getTotalPassengers(self):
        pass

    def getVehicleTypeCost(self):
        pass

    def getSpecialVehicleCost(self):
        pass

    def getFlowCost(self):
        pass

    def getTimeSinceLastGreen(self):
        pass

    def getEmissions(self):
        pass

    def _getOncomingVehicles(self, headingTol=15):
        # Oncoming if (in active lane & heading matches oncoming heading & 
        # is in lane bounds)
        vehicles = []
        targetLanes = []
        for edges in self.getActiveEdges():
            for edge in self.controlledEdges[edges]:
                targetLanes += self.edgeLaneMap[edge]

        for lane in targetLanes:
            laneHeading = self.allLaneInfo[lane]['heading']
            headingUpper = laneHeading + headingTol
            headingLower = laneHeading - headingTol
            laneBounds = self.allLaneInfo[lane]['bounds']
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
                              .stages[self.mode][self.lastStageIndex]\
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

    def getActiveEdges(self):
        return sigTools.lane2edge(self._getActiveLanes())

    def _getActiveLanesDict(self):
        # Get the current control string to find the green lights
        activeLanesDict = {}
        for n, stage in enumerate(self.junctionData.stages[self.mode]):
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
            distance = sigTools.getDistance(vehPosition, self.jcnPosition)
            # sumo defines a vehicle as halted if v< 0.01 m/s
            if distance > maxDistance \
              and self.CAM.receiveData[ID]['v'] < haltVelocity:
                furthestID = ID
                maxDistance = distance

        return [furthestID, maxDistance]

    def _getNearestVehicle(self, vehIDs, minDistance=28):
        nearestID = ''
        
        for ID in vehIDs:
            vehPosition = np.array(self.CAM.receiveData[ID]['pos'])
            distance = sigTools.getDistance(vehPosition, self.jcnPosition)
            if distance < minDistance:
                nearestID = ID
                minDistance = distance

        return {'id': nearestID, 'distance': minDistance}

    def _getLaneDetectTime(self):
        activeLanes = self._getActiveLanes()
        meanDetectTimePerLane = []
        retrievedEdges = []
        flowConst = tc.LAST_STEP_TIME_SINCE_DETECTION
        edges = sigTools.unique([lane.split('_')[0] for lane in activeLanes])
        for edge in edges:
            detectTimes = []
            for loop in self.laneInductors[edge]:
                detectTimes.append(self.subResults[loop][flowConst])
            meanDetectTimePerLane.append(detectTimes)

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
        detectTimes = sigTools.flatten(self._getLaneDetectTime())
        detectTimes = np.array(detectTimes)
        if not detectTimes.any():
            return None
        # Set adaptive time limit
        try:
            cond1 = np.any(detectTimes <= self.threshold)
            #cond2 = np.std(detectTimes) < 2*self.threshold
            #cond3 = np.mean(detectTimes) < 3*self.threshold
        except Exception as e:
            print(self._getActiveLanes(), detectTimes)
            raise(e)
        if cond1:
            loopExtend = self.extendTime
        else:
            loopExtend = 0.0
        return loopExtend

    def getGPSextension(self):
        # If active and on the second, or transition then make stage descision
        oncomingVeh = self._getOncomingVehicles()
        haltVelocity = 0.01
        # If currently staging then extend time if there are vehicles close 
        # to the stop line.
        catchDistance = self.getNearVehicleCatchDistance()
        nearestVeh = self._getNearestVehicle(oncomingVeh, catchDistance)
        
        # nV[1] is its velocity
        # If a vehicle detected and within catch distance
        if (nearestVeh['id'] != '') and (nearestVeh['distance'] <= catchDistance):
            # if not invalid and travelling faster than SPM velocity
            vdata = self.CAM.receiveData[nearestVeh['id']]
            if (vdata['v'] > haltVelocity):
                dt = abs(self.TIME_SEC - vdata['Tgen'])
                distance = abs(nearestVeh['distance'] - vdata['v']*dt)
                distance = sigTools.ceilRound(distance, 0.1)
                gpsExtend = distance/vdata['v']
                gpsExtend = sigTools.ceilRound(distance/vdata['v'], 0.1)

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

    def getQueueExtension(self):
        oncomingVeh = self._getOncomingVehicles()
        # If new stage get furthest from stop line whose velocity < 5% speed
        # limit and determine queue length
        furthestVehDist = self._getFurthestStationaryVehicle(oncomingVeh)
        # secondsPerMeterTraffic = self.getSecondsPerMeterTraffic()
        # secondsPerMeterTraffic = 0.3  # reach max green by 200m
        if furthestVehDist[0] != '':
            queueExtend = ceil(self.secPerMeterTraffic*furthestVehDist[1])
        # If we're in this state this should never happen but just in case
        else:
            queueExtend = 0.0
        return queueExtend

    def getSecondsPerMeterTraffic(self):
        activeLanes = self._getActiveLanes()
        spmts = [self.secondsPerMeterTrafficDict[lane] for lane in activeLanes]
        return max(spmts)

    def getNearVehicleCatchDistance(self):
        activeLanes = self._getActiveLanes()
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
