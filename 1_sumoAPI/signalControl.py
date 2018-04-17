#!/usr/bin/env python
"""
@file    signalControl.py
@author  Simon Box
@date    31/01/2013

Parent class for signal control algorithms

"""
import traciLink, traci
import traci.constants as tc

class signalControl(object):
    
    def __init__(self):
        self.transitionObject = stageTransition()
        traci.simulation.subscribe(varIDs=(tc.VAR_TIME_STEP,))
        
    def process(self, simtime=None):
        self.transitionObject.processTransition(simtime)
        
    def getCurrentSUMOtime(self):
        #return traci.simulation.getCurrentTime()
        return traci.simulation.getSubscriptionResults()[tc.VAR_TIME_STEP]

    def setAmberTime(self, time):
        self.transitionObject.setAmberTime(time)
        
    def setAllRedTime(self, time):
        self.transitionObject.setAllRedTime(time)
    
    
class stageTransition(object):
        
        def __init__(self): 
            self.setAmberTime(3)
            self.setAllRedTime(1)
            self.active=False
            traci.simulation.subscribe(varIDs=(tc.VAR_TIME_STEP,))
        
        def setAmberTime(self, time):
            self.amberTime = time
        
        def setAllRedTime(self, time):
            self.allRed = time
            
        def getCurrentSUMOtime(self):
            #return traci.simulation.getCurrentTime()
            return traci.simulation.getSubscriptionResults()[tc.VAR_TIME_STEP]
        
        def newTransition(self, junctionID, currentStageString, targetStageString, simtime=None):
            if len(currentStageString) != len(targetStageString):
                print("Error current stage string and target stage sting are different lengths")
            
            self.amberStageString=""
            self.allRedStageString=""
            i = 0
            while i < len(currentStageString):
                if targetStageString[i]=='r' and (currentStageString[i]=='G' or currentStageString[i]=='g'):
                    self.amberStageString = self.amberStageString + 'y'
                    self.allRedStageString = self.allRedStageString + 'r'
                else:
                    self.amberStageString = self.amberStageString + currentStageString[i]
                    self.allRedStageString = self.allRedStageString + currentStageString[i]
                i += 1
            
            self.targetStageString = targetStageString
            self.junctionID = junctionID
            self.transitionStart = simtime if simtime != None else self.getCurrentSUMOtime()
            self.active = True
        
        def processTransition(self, simtime=None):             
            if self.active:
                simTime = simtime if simtime != None else self.getCurrentSUMOtime()
                if (simTime - self.transitionStart) < (self.amberTime*1000):
                    traci.trafficlights.setRedYellowGreenState(self.junctionID, self.amberStageString)
                elif (simTime - self.transitionStart) < ((self.amberTime + self.allRed)*1000):
                    traci.trafficlights.setRedYellowGreenState(self.junctionID, self.allRedStageString)
                else:
                    traci.trafficlights.setRedYellowGreenState(self.junctionID, self.targetStageString)
                    self.active=False
            else:
                pass
                 