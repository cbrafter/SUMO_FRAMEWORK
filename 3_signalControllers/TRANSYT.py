#!/usr/bin/env python
"""
@file    fixedTimeControl.py
@author  Simon Box
@date    31/01/2013

class for fixed time signal control

"""
import signalControl, readJunctionData, traci
import signalTools as sigTools

class TRANSYT(signalControl.signalControl):
    def __init__(self, junctionData):
        super(TRANSYT, self).__init__()
        self.junctionData = junctionData
        self.setTransitionTime(self.junctionData.id)

        self.TIME_MS = self.getCurrentSUMOtime()
        self.TIME_SEC = 0.001 * self.TIME_MS
        self.firstCalled = self.TIME_MS
        self.lastCalled = self.TIME_MS
        self.lastStageIndex = 0
        mode = self.getMode()
        self.Nstages = len(self.junctionData.stages[mode])

        # Pedestrian parameters (1.2 m/s walking speed)
        self.pedTime = 1000 * sigTools.getJunctionDiameter(self.junctionData.id)/1.2
        self.pedStage = False
        self.pedCtrlString = 'r'*len(self.junctionData.stages[mode][self.lastStageIndex].controlString)
        juncsWithPedStages = ['junc0', 'junc9', 'junc1', 'junc10',
                              'junc4', 'junc5', 'junc6', 'junc7']
        if self.junctionData.id in juncsWithPedStages:
            self.hasPedStage = True 
        else:
            self.hasPedStage = False

        traci.trafficlights.setRedYellowGreenState(self.junctionData.id, 
            self.junctionData.stages[mode][self.lastStageIndex].controlString)
        
    def process(self, time=None):
        self.TIME_MS = time if time is not None else self.getCurrentSUMOtime()
        self.TIME_SEC = 0.001 * self.TIME_MS
        mode = self.getMode()

        if self.transitionObject.active:
            # If the transition object is active i.e. processing a transition
            pass
        elif (self.TIME_MS - self.firstCalled) < (self.junctionData.offset*1000):
            # Process offset first
            pass
        elif not self.pedStage and ((self.TIME_MS - self.lastCalled) <
              (self.junctionData.stages[mode][self.lastStageIndex].period*1000)):
            # Before the period of the next stage
            pass
        elif self.pedStage and (self.TIME_MS - self.lastCalled) < self.pedTime:
            pass
        else:
            nextStageIndex = (self.lastStageIndex + 1) % self.Nstages
            # We have completed one cycle, DO ped stage
            if self.hasPedStage and nextStageIndex == 0 and not self.pedStage:
                self.pedStage = True
                lastStage = self.junctionData.stages[mode][self.lastStageIndex].controlString
                nextStage = self.pedCtrlString
            # Completed ped stage, resume signalling
            elif self.hasPedStage and self.pedStage:
                self.pedStage = False
                lastStage = self.pedCtrlString
                nextStage = self.junctionData.stages[mode][nextStageIndex].controlString
                self.lastStageIndex = nextStageIndex
            # No ped action, normal cycle
            else:
                lastStage = self.junctionData.stages[mode][self.lastStageIndex].controlString
                nextStage = self.junctionData.stages[mode][nextStageIndex].controlString
                self.lastStageIndex = nextStageIndex
            
            self.transitionObject.newTransition(
                self.junctionData.id, lastStage, nextStage)
            self.lastCalled = self.TIME_MS

        super(TRANSYT, self).process(self.TIME_MS)
        return None

    def getTimeToSignalChange(self):
        return (self.junctionData.stages[self.getMode()][self.lastStageIndex].period*1000 - 
            (self.TIME_MS - self.lastCalled))

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
