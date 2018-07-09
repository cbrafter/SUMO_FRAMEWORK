#!/usr/bin/env python
"""
@file    fixedTimeControl.py
@author  Simon Box
@date    31/01/2013

class for fixed time signal control

"""
import signalControl, readJunctionData, traci

class TRANSYT(signalControl.signalControl):
    def __init__(self, junctionData):
        super(fixedTimeControl, self).__init__()
        self.junctionData = junctionData
        self.setTransitionTime(self.junctionData.id)
        self.TIME_MS = self.getCurrentSUMOtime()
        self.firstCalled = self.TIME_MS
        self.lastCalled = self.TIME_MS
        self.lastStageIndex = 0
        mode = self.getMode()
        self.Nstages = len(self.junctionData.stages[mode])
        traci.trafficlights.setRedYellowGreenState(self.junctionData.id, 
            self.junctionData.stages[mode][self.lastStageIndex].controlString)
        
    def process(self, time=None):
        self.TIME_MS = self.getCurrentSUMOtime() if time is None else time
        self.TIME_SEC = 0.001 * self.TIME_MS
        mode = self.getMode()

        if self.transitionObject.active:
            # If the transition object is active i.e. processing a transition
            pass
        elif (self.TIME_MS - self.firstCalled) < (self.junctionData.offset*1000):
            # Process offset first
            pass
        elif (self.TIME_MS - self.lastCalled) < (self.junctionData.stages[self.lastStageIndex].period*1000):
            # Before the period of the next stage
            pass
        else:
            nextStageIndex = (self.lastStageIndex + 1) % self.Nstages
            self.transitionObject.newTransition(
                self.junctionData.id, 
                self.junctionData.stages[mode][self.lastStageIndex].controlString,
                self.junctionData.stages[mode][nextStageIndex].controlString)
            self.lastStageIndex = nextStageIndex

            self.lastCalled = self.TIME_MS
                
        super(TRANSYT, self).process(self.TIME_MS)
        return None

    def getTimeToSignalChange(self):
        return (self.junctionData.stages[self.lastStageIndex].period*1000 - 
            (self.TIME_MS - self.lastCalled))

    def getMode(self):
        time = self.TIME_SEC % 86400  # modulo 1 day in seconds for spill over
        # 00:00 - 06:00
        if 0 <= time < 21600:
            return 'OFF'
        # 06:00 - 11:00    
        elif 21600 <= time < 39600:
            return 'PEAK'
        # 11:00 - 16:00
        elif 39600 <= time < 57600:
            return 'INTER'
        # 16:00 - 20:00
        elif 57600 <= time < 72000:
            return 'PEAK'
        # 20:00 - 00:00
        elif 72000 <= time < 86400:
            return 'OFF'
        else:
            return 'INTER'
