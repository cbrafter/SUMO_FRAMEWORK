#!/usr/bin/env python
"""
@file    fixedTimeControl.py
@author  Simon Box
@date    31/01/2013

class for fixed time signal control

"""
import signalControl, readJunctionData, traci

class fixedTimeControl(signalControl.signalControl):
    def __init__(self, junctionData):
        super(fixedTimeControl, self).__init__()
        self.junctionData = junctionData
        super(fixedTimeControl, self).setTransitionTime(self.junctionData.id)
        self.firstCalled = self.getCurrentSUMOtime()
        self.lastCalled = self.getCurrentSUMOtime()
        self.lastStageIndex = 0
        traci.trafficlights.setRedYellowGreenState(self.junctionData.id, 
            self.junctionData.stages[self.lastStageIndex].controlString)
        
    def process(self):
        if self.transitionObject.active:
            # If the transition object is active i.e. processing a transition
            pass
        elif (self.getCurrentSUMOtime() - self.firstCalled) < (self.junctionData.offset*1000):
            # Process offset first
            pass
        elif (self.getCurrentSUMOtime() - self.lastCalled) < (self.junctionData.stages[self.lastStageIndex].period*1000):
            # Before the period of the next stage
            pass
        else:
            nextStageIndex = (self.lastStageIndex + 1) %\
                             len(self.junctionData.stages)
            self.transitionObject.newTransition(
                self.junctionData.id, 
                self.junctionData.stages[self.lastStageIndex].controlString,
                self.junctionData.stages[nextStageIndex].controlString)
            self.lastStageIndex = nextStageIndex

            self.lastCalled = self.getCurrentSUMOtime()
                
        super(fixedTimeControl, self).process()

    def getTimeToSignalChange(self):
        return (self.junctionData.stages[self.lastStageIndex].period*1000 - 
            (self.getCurrentSUMOtime() - self.lastCalled))
