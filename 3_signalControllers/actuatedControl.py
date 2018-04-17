#!/usr/bin/env python
"""
@file    actuatedControl.py
@author  Craig Rafter
@date    15/08/2016

class for fixed time signal control

"""
import signalControl, readJunctionData, traci
import numpy as np
from collections import defaultdict
import traci.constants as tc


class actuatedControl(signalControl.signalControl):
    def __init__(self, junctionData, minGreenTime=10, maxGreenTime=60, extendTime=1):
        super(actuatedControl, self).__init__()
        self.junctionData = junctionData
        self.Nstages = len(self.junctionData.stages)
        self.firstCalled = traci.simulation.getCurrentTime()
        self.lastCalled = self.firstCalled
        self.lastStageIndex = 0
        traci.trafficlights.setRedYellowGreenState(self.junctionData.id, 
            self.junctionData.stages[self.lastStageIndex].controlString)
        
        self.minGreenTime = minGreenTime
        self.maxGreenTime = maxGreenTime
        self.extendTime = 1.0
        self.stageTime = 0.0
        self.threshold = 2.5
        self.controlledLanes = traci.trafficlights.getControlledLanes(self.junctionData.id)
        self.laneInductors = self._getLaneInductors()

        self.TIME_MS = self.firstCalled
        self.TIME_SEC = 0.001 * self.TIME_MS

        traci.junction.subscribeContext(self.junctionData.id, 
            tc.CMD_GET_INDUCTIONLOOP_VARIABLE, 
            50, 
            varIDs=(tc.LAST_STEP_TIME_SINCE_DETECTION,))


    def process(self):
        self.TIME_MS = self.getCurrentSUMOtime()
        self.TIME_SEC = 0.001 * self.TIME_MS
        self.stageTime = max(self.minGreenTime, self.stageTime)
        self.stageTime = min(self.stageTime, self.maxGreenTime)
        # Is the 1 sec control interval
        isControlInterval = not self.TIME_MS % 1000
                
        # Get actuation information and make actuation decision once per second
        if isControlInterval:
            # Get loop subscriptions
            self.getSubscriptionResults()
            detectTimePerLane = self._getLaneDetectTime()
            # Set adaptive time limit
            # print(self.junctionData.id, detectTimePerLane)
            if np.any(detectTimePerLane < self.threshold):
                extend = self.extendTime
            else:
                extend = 0.0

            elapsedTime = 0.001*(self.TIME_MS - self.lastCalled)
            Tremaining = self.stageTime - elapsedTime
            self.stageTime = elapsedTime + max(extend, Tremaining)
            self.stageTime = min(self.stageTime, self.maxGreenTime)

            # self.stageTime = max(self.stageTime + extend, self.minGreenTime)
            # self.stageTime = min(self.stageTime, self.maxGreenTime)
        else:
            pass
        
        if isControlInterval:
            # Process light state
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
                # Not active, not in offset, stage not finished, loop stages
                # stage index must be int
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
        
        super(actuatedControl, self).process(self.TIME_MS)


    def getSubscriptionResults(self):
        self.subResults = traci.junction.getContextSubscriptionResults(self.junctionData.id)


    def _getActiveLanes(self):
        # Get the current control string to find the green lights
        stageCtrlString = self.junctionData.stages[self.lastStageIndex].controlString
        activeLanes = []
        for i, letter in enumerate(stageCtrlString):
            if letter == 'G':
                activeLanes.append(self.controlledLanes[i])
        # Get a list of the unique 
        activeLanes = list(np.unique(np.array(activeLanes)))
        return activeLanes


    def _getLaneInductors(self):
        laneInductors = defaultdict(list)

        for loop in traci.inductionloop.getIDList():
            loopLane = traci.inductionloop.getLaneID(loop)
            if loopLane in self.controlledLanes:
                laneInductors[loopLane].append(loop)
            
        return laneInductors


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
