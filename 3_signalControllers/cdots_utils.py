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


class stageOptimiser():
    def __init__(self, signalController):
        self.signalController = signalController

    def getNextStageIndex(self):
        laneCosts = np.array(self.getLaneCosts())
        return laneCosts.argmax()

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
