#!/usr/bin/env python
"""
@file    signalControl.py
@author  Simon Box
@date    31/01/2013

Parent class for signal control algorithms

"""
import traciLink, traci
import traci.constants as tc
import math
from scipy.spatial import distance
import numpy as np


def getIntergreen(dist):
    # <10 & 10-18 & 19-27 & 28-37 & 38-46 & 47-55 & 56-64 & >65
    #  5  &   6   &   7   &   8   &   9   &  10   &  11   & 12
    diamThresholds = [10, 19, 28, 38, 47, 56, 65]
    intergreen = 5
    for threshold in diamThresholds:
        if dist < threshold:
            return intergreen
        else:
            intergreen += 1
    return intergreen


class signalControl(object):
    
    def __init__(self):
        self.transitionObject = stageTransition()
        traci.simulation.subscribe(varIDs=(tc.VAR_TIME_STEP,))
        
    def process(self, simtime=None):
        self.transitionObject.processTransition(simtime)
        
    def getCurrentSUMOtime(self):
        #return traci.simulation.getCurrentTime()
        return traci.simulation.getSubscriptionResults()[tc.VAR_TIME_STEP]

    def setAmber1Time(self, time):
        self.transitionObject.setAmber1Time(time)

    def setAmber2Time(self, time):
        self.transitionObject.setAmber2Time(time)
    
    def setAllRedTime(self, time):
        self.transitionObject.setAllRedTime(time)

    def getIntergreenTime(self, junctionID):
        x1, y1 = traci.junction.getPosition(junctionID)
        edges = traci.trafficlights.getControlledLinks(junctionID)
        edges = [x for z in edges for y in z for x in y[:2]]
        edges = list(set(edges))
        boundingCoords = []
        for edge in edges:
            dMin, coordMin = 1e6, []
            for x2, y2 in traci.lane.getShape(edge):
                dist = math.hypot(x2-x1, y2-y1)
                if dist < dMin:
                    dMin, coordMin = dist, [x2, y2]
            boundingCoords.append(coordMin)
        # get max of closest edge pairwise distances
        dMax = np.max(distance.cdist(boundingCoords, boundingCoords))
        return getIntergreen(dMax)

    def setTransitionTime(self, junctionID):
        amber1 = 3
        red = 2
        amber2 = abs(self.getIntergreenTime(junctionID) - (amber1 + red))
        if amber2 > 3:
            red += amber2 - 3
            amber2 = 3

        self.setAllRedTime(red)
        self.setAmber1Time(amber1)
        self.setAmber2Time(amber2)

    
class stageTransition(object):
    def __init__(self): 
        self.setAmber1Time(3)
        self.setAmber2Time(0)
        self.setAllRedTime(1)
        self.active=False
        traci.simulation.subscribe(varIDs=(tc.VAR_TIME_STEP,))
        # current+target -> amber1,amber2,allRed
        self.transitionDict = {'rr': 'rrr', 'GG': 'GGG', 'gg': 'ggg',
                               'rg': 'ryr', 'Gr': 'yrr', 'gr': 'yrr',
                               'rG': 'ryr', 'Gg': 'Ggg', 'gG': 'gGg'}
    
    def setAmber1Time(self, time):
        self.amber1Time = time

    def setAmber2Time(self, time):
        self.amber2Time = time
    
    def setAllRedTime(self, time):
        self.allRed = time
        
    def getCurrentSUMOtime(self):
        #return traci.simulation.getCurrentTime()
        return traci.simulation.getSubscriptionResults()[tc.VAR_TIME_STEP]
    
    def newTransition(self, junctionID, currentStageString, targetStageString, simtime=None):
        if len(currentStageString) != len(targetStageString):
            print("Error current stage string and target stage sting are different lengths")
        
        self.amber1StageString=""
        self.amber2StageString=""
        self.allRedStageString=""
        
        for current, target in zip(currentStageString, targetStageString):
            transitionString = self.transitionDict[current+target]
            self.amber1StageString += transitionString[0]
            self.amber2StageString += transitionString[1]
            self.allRedStageString += transitionString[2]
        
        self.targetStageString = targetStageString
        self.junctionID = junctionID
        self.transitionStart = simtime if simtime != None\
                                       else self.getCurrentSUMOtime()
        self.active = True
    
    def processTransition(self, simtime=None):             
        if self.active:
            simTime = simtime if simtime != None else self.getCurrentSUMOtime()
            transitionTimeDelta = simTime - self.transitionStart
            amber1Threshold = self.amber1Time*1000
            allRedThreshold = amber1Threshold + self.allRed*1000
            amber2Threshold = allRedThreshold + self.amber2Time*1000
            self.stageString = ''
            # First amber
            if transitionTimeDelta < amber1Threshold:
                self.makeTransition(self.amber1StageString)
            # All Red
            elif transitionTimeDelta < allRedThreshold:
                self.makeTransition(self.allRedStageString)
            # Second Amber
            elif transitionTimeDelta < amber2Threshold:
                self.makeTransition(self.amber2StageString)
            # Target Stage
            elif transitionTimeDelta >= amber2Threshold:
                self.makeTransition(self.targetStageString)
                self.active=False
            else:
                pass
        else:
            pass
    
    def makeTransition(self, transitionStageString):
        if self.stageString != transitionStageString:
            traci.trafficlights.setRedYellowGreenState(self.junctionID,
                                                       transitionStageString)
            self.stageString = transitionStageString
