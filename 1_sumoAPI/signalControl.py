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
import signalTools as sigTools
import re

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

    def setTransitionTime(self, junctionID):
        amber1 = 3
        red = 2
        amber2 = abs(sigTools.getIntergreenTime(junctionID) - (amber1 + red))
        if amber2 > 3:
            red += amber2 - 3
            amber2 = 3

        self.setAllRedTime(red)
        self.setAmber1Time(amber1)
        self.setAmber2Time(amber2)
        self.intergreen = red + amber1 + amber2

    def setModelName(self, model):
        self.modelName = model

    def getModelRoutes(self):
        file = open('../2_models/VALIDROUTES/{}_valid_routes.rou.xml'\
                    .format(self.modelName), 'r')
        regex = re.compile('edges="(.+?)"')
        routes = []
        for line in file:
            match  = regex.search(line)
            if not match:
                continue
            else:
                routes.append(match.groups()[0].split(' '))
        return routes

    
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
        # API Calls are expensive so only call if needed to change stage 
        # the first time
        if self.stageString != transitionStageString:
            traci.trafficlights.setRedYellowGreenState(self.junctionID,
                                                       transitionStageString)
            self.stageString = transitionStageString
