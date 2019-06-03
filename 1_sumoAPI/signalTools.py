#!/usr/bin/env python
"""
@file    signalTools.py
@author  Craig Rafter
@date    09/05/2018

class for fixed time signal control
"""

import traci
from collections import defaultdict
from math import atan2, degrees, ceil, hypot, floor
import re
from glob import glob
import os
from scipy.spatial import distance
import numpy as np
import traci.constants as tc
import time
from psutil import cpu_count
import sys
import itertools
import traceback


def getIntergreen(dist):
    # diam (m) <10 & 10-18 & 19-27 & 28-37 & 38-46 & 47-55 & 56-64 & >65
    # time (s)  5  &   6   &   7   &   8   &   9   &  10   &  11   &  12
    diamThresholds = [10, 19, 28, 38, 47, 56, 65]
    intergreen = 5
    for threshold in diamThresholds:
        if dist < threshold:
            return intergreen
        else:
            intergreen += 1
    return intergreen


def getJunctionDiameter(junctionID):
    juncPos = traci.junction.getPosition(junctionID)
    edges = traci.trafficlights.getControlledLinks(junctionID)
    edges = [x for z in edges for y in z for x in y[:2]]
    edges = list(set(edges))
    boundingCoords = []
    for edge in edges:
        dMin, coordMin = 1e6, []
        for laneCoord in traci.lane.getShape(edge):
            dist = getDistance(juncPos, laneCoord)
            if dist < dMin:
                dMin, coordMin = dist, laneCoord
        boundingCoords.append(coordMin)
    # get max of closest edge pairwise distances
    dMax = np.max(distance.cdist(boundingCoords, boundingCoords))
    return dMax


def getIntergreenTime(junctionID):
    juncDiameter = getJunctionDiameter(junctionID)
    return getIntergreen(juncDiameter)


def getSUMOHeading(currentLoc, prevLoc):
    dy = currentLoc[1] - prevLoc[1]
    dx = currentLoc[0] - prevLoc[0]
    if currentLoc[1] == prevLoc[1] and currentLoc[0] == prevLoc[0]:
        heading = -1
    else:
        if dy >= 0:
            heading = degrees(atan2(dy, dx))
        else:
            heading = 360 + degrees(atan2(dy, dx))
    
    # Map angle to make compatible with SUMO heading
    if 0 <= heading <= 90:
        heading = 90 - heading
    elif 90 < heading < 360:
        heading = 450 - heading

    return heading


def unique(sequence):
    return list(set(sequence))


def mean(x):
    return sum(x)/float(len(x))


def getIncomingLaneInfo(controlledLanes):
    laneInfo = {}
    for lane in unique(controlledLanes):
        shape = traci.lane.getShape(lane)
        width = traci.lane.getWidth(lane)
        heading = getSUMOHeading(shape[-1], shape[0])
        x1, y1 = shape[0]
        x2, y2 = shape[-1]
        dx = abs(x2 - x1) 
        dy = abs(y2 - y1)
        if dx > dy:
            y1 += width
            y2 -= width
        else: 
            x1 += width
            x2 -= width
        laneInfo[lane] = {'heading': heading, 
                          'bounds': {'x1': x1, 'y1': y1,
                                     'x2': x2, 'y2': y2}
                         }
    return laneInfo


def getRouteDict():
    fileNames = glob('../2_models/VALIDROUTES/*.rou.xml')
    models = []
    regex = re.compile('.+edges="(.+?)"')
    routeDict = {}

    for fileName in fileNames:
        file = open(fileName, 'r')
        model = os.path.basename(fileName).split('_')[0]
        routeDict[model] = []
        for line in file:
            match = regex.match(line)
            if not match:
                continue
            else:
                routeDict[model].append(match.groups()[0].split())
        file.close()

    return routeDict


def isInRange(vehPosition, scanRange, jcnGeometry):
    # center, JCR = jcnGeometry # jcnPos, jcnCtrlRegion
    # distance = hypot(*(vehPosition - jcnGeometry[0]))
    c1 = hypot(*(vehPosition - jcnGeometry[0])) < scanRange
    # shorten variable name and check box is in bounds
    c2 = jcnGeometry[1]['W'] <= vehPosition[0] <= jcnGeometry[1]['E']
    c3 = jcnGeometry[1]['S'] <= vehPosition[1] <= jcnGeometry[1]['N']
    return (c1 and c2 and c3)


# default dict that finds and remembers road speed limits (only if static)
# needs to be updated otherwise
class speedLimDict(defaultdict):
    def __missing__(self, key):
        self[key] = traci.lane.getMaxSpeed(key)
        return self[key]


# defaultdict that finds and remembers vehicle types (only if static)
# needs to be updated otherwise
class vTypeDict(defaultdict):
    def __missing__(self, key):
        self[key] = traci.vehicle.getTypeID(key)
        return self[key]


class emissionDict(defaultdict):
    def __missing__(self, key):
        # CO2 = tc.VAR_CO2EMISSION
        # CO = tc.VAR_COEMISSION
        # HC = tc.VAR_HCEMISSION
        # PMX = tc.VAR_PMXEMISSION
        # NOX = tc.VAR_NOXEMISSION
        # FUEL = tc.VAR_FUELCONSUMPTION
        self[key] = {tc.VAR_CO2EMISSION: 0.0,
                     tc.VAR_COEMISSION: 0.0,
                     tc.VAR_HCEMISSION: 0.0,
                     tc.VAR_PMXEMISSION: 0.0,
                     tc.VAR_NOXEMISSION: 0.0,
                     tc.VAR_FUELCONSUMPTION: 0.0}
        return self[key]



def getDistance(A, B):
    # x1, y1 = A
    # x2, y2 = B
    # return hypot(x1-x2, y1-y2)
    return hypot(A[0]-B[0], A[1]-B[1])


def flatten(listOfLists):
    return [elem for subList in listOfLists for elem in subList]


class StopCounter(object):
    def __init__(self):
        self.stopCountDict = defaultdict(int)
        self.waitingDict = defaultdict(float)
        self.WAIT = tc.VAR_WAITING_TIME
        self.speedTol = 1e-3
        self.stopSubscription()  # makes self.subkey

    def stopSubscription(self):
        self.subkey = [e for e in traci.edge.getIDList() if ':' not in e][0]
        traci.edge.subscribeContext(self.subkey, 
                                    tc.CMD_GET_VEHICLE_VARIABLE, 
                                    1000000, 
                                    varIDs=(self.WAIT,))

    def getSubscriptionResults(self):
        return traci.edge.getContextSubscriptionResults(self.subkey)

    def getStops(self):
        self.subResults = self.getSubscriptionResults()
        
        try:
            for vehID in self.subResults.keys():
                if self.subResults[vehID][self.WAIT] > 0.0:
                    self.waitingDict[vehID] += 0.1
                if 0.099 < self.subResults[vehID][self.WAIT] < 0.101:
                    self.stopCountDict[vehID] += 1
        except KeyError:
            pass
        except AttributeError:
            pass

    def writeStops(self, filename):
        with open(filename, 'w') as f:
            f.write('vehID,stops\n')
            vehIDs = self.stopCountDict.keys()
            vehIDs.sort()
            for vehID in vehIDs:
                f.write('{},{}\n'.format(vehID, self.stopCountDict[vehID]))


class EmissionCounter(object):
    def __init__(self):
        self.emissionCountDict = emissionDict()
        self.emissionMonitor = emissionDict()
        self.vTypeDict = defaultdict(lambda: 'car')
        self.CO2 = tc.VAR_CO2EMISSION
        self.CO = tc.VAR_COEMISSION
        self.HC = tc.VAR_HCEMISSION
        self.PMX = tc.VAR_PMXEMISSION
        self.NOX = tc.VAR_NOXEMISSION
        self.FUEL = tc.VAR_FUELCONSUMPTION
        self.emissionList = [self.CO2, self.CO, self.HC,
                             self.PMX, self.NOX, self.FUEL]
        self.vType = tc.VAR_TYPE
        self.EmissionSubscription()  # makes self.subkey

    def EmissionSubscription(self):
        self.subkey = [e for e in traci.edge.getIDList() if ':' not in e][0]
        traci.edge.subscribeContext(self.subkey, 
                                    tc.CMD_GET_VEHICLE_VARIABLE, 
                                    1000000, 
                                    varIDs=(self.CO2, self.CO, self.HC,
                                            self.PMX, self.NOX, self.FUEL,
                                            self.vType))

    def getSubscriptionResults(self):
        return traci.edge.getContextSubscriptionResults(self.subkey)
        
    def getEmissionsOLD(self, time):
        self.subResults = self.getSubscriptionResults()

        try:
            # If new second, add per second emissions to total
            if not time%1000:
                for vehID in self.subResults.keys():
                    if vehID not in self.vTypeDict.keys():
                        self.vTypeDict[vehID] = self.subResults[vehID][self.vType]
                    # Add max per second counts to total
                    for emission in self.emissionList:
                        self.emissionCountDict[vehID][emission] += \
                            self.emissionMonitor[vehID][emission]

                # reset monitor for next second
                self.emissionMonitor = emissionDict()

            # Check for max per second emissions in this time step
            for vehID in self.subResults.keys():
                # Track maximum per second emissions
                for emission in self.emissionList:
                    self.emissionMonitor[vehID][emission] = \
                        max(self.emissionMonitor[vehID][emission],
                            self.subResults[vehID][emission])
        except KeyError:
            pass
            # print("Emissions Writer: KeyError")
            # traceback.print_exc()
        except AttributeError:
            pass
            # print("Emissions Writer: AttributeError")
            # traceback.print_exc()

    def getEmissions(self, time):
        self.subResults = self.getSubscriptionResults()

        try:
            # If new second, add per second emissions to total
            if not time%1000:
                for vehID in self.subResults.keys():
                    if vehID not in self.vTypeDict.keys():
                        self.vTypeDict[vehID] = self.subResults[vehID][self.vType]
                    for emission in self.emissionList:
                        # Track maximum per second emissions
                        self.emissionMonitor[vehID][emission] = \
                            max(self.emissionMonitor[vehID][emission],
                                self.subResults[vehID][emission])
                        # Add max per second counts to total
                        self.emissionCountDict[vehID][emission] += \
                            self.emissionMonitor[vehID][emission]

                # reset monitor for next second
                self.emissionMonitor = emissionDict()

            else:
                # Check for max per second emissions in this time step
                for vehID in self.subResults.keys():
                    # Track maximum per second emissions
                    for emission in self.emissionList:
                        self.emissionMonitor[vehID][emission] = \
                            max(self.emissionMonitor[vehID][emission],
                                self.subResults[vehID][emission])
        except KeyError:
            pass

        except AttributeError:
            pass

    def writeEmissions(self, filename):
        with open(filename, 'w') as f:
            f.write('vehID,vType,CO2,CO,HC,PMX,NOX,FUEL\n')
            vehIDs = self.emissionCountDict.keys()
            vehIDs.sort()
            for vehID in vehIDs:
                dataStr = '{},{},'.format(vehID, self.vTypeDict[vehID])
                for emission in self.emissionList:
                    dataStr += str(self.emissionCountDict[vehID][emission])
                    dataStr += ','
                # Don't write terminating comma
                dataStr = dataStr[:-1] + '\n'
                f.write(dataStr)

class simTimer(object):
    def __init__(self):
        self.startTime = 0
        self.stopTime = 0
        self.started = False
        self.stopped = False

    def start(self):
        if not self.started:
            self.startTime = time.time()
            self.started = True
        else:
            print('WARNING: Timer already started')

    def stop(self):
        if self.started and not self.stopped:
            self.stopTime = time.time()
            self.stopped = True
        else:
            print('WARNING: Timer already stopped/not active')

    def runtime(self):
        if self.started and self.stopped: 
            return self.stopTime - self.startTime
        elif self.started and not self.stopped:
            return time.time() - self.startTime
        else:
            print('WARNING: Timer not active')
            return -1

    def strTime(self):
        return time.strftime("%dd %X", time.gmtime(self.runtime()))


def getNproc(mode='best'):
    mode = mode.lower()
    physical = cpu_count(logical=False)
    logical = cpu_count()
    if mode == 'best':
        return np.mean([physical, logical], dtype=int)
    elif mode in ['max', 'logical']:
        return logical
    elif mode in ['phy', 'physical']:
        return physical
    elif mode == 'low':
        return max(1, int(physical/2.))
    else:
        return 1


def isSimGridlocked(model, timeMS):

    timeHours = timeMS/3600000.0
    forceSimEndTime = 40.0 if 'selly' in model else 6.0

    if timeHours >= forceSimEndTime:
        print('TIMEOUT: {} >= {} on {}'.format(timeHours, forceSimEndTime, model))
        sys.stdout.flush()
        return True

    try:
        vehIDs = traci.vehicle.getIDList()
        isStationary = []
        isWaiting = []
        for vID in vehIDs:
            isStationary.append(traci.vehicle.getSpeed(vID) < 0.1)
            # vehicle is waiting too long if all cycles complete and still blocked
            isWaiting.append(traci.vehicle.getWaitingTime(vID) > 500.0)


        if all(isStationary) and all(isWaiting):
            meanStationary = np.mean(isStationary)
            meanWaiting = np.mean(isWaiting)
            if 'nan' in [str(meanStationary), str(isWaiting)]:
                return False
            print('GRIDLOCK: all vehicles stationary, hour: {}'.format(timeHours))
            print('GRIDLOCK: stopped {} waiting {}'.format(meanStationary, meanWaiting))
            sys.stdout.flush()
            return True
        else:
            return False
    except:
        print(isStationary)
        print(isWaiting)
        return False


def lane2edge(lanes):
    if type(lanes) is str:
        return unique([lanes.split('_')[0]])
    elif type(lanes) is list:
        return unique([x.split('_')[0] for x in lanes])
    else:
        raise TypeError("lanes not list or string")

def edge2lanes(edges, laneNdict):
    lanes = []
    if type(edges) is str:
        eList = [edges]
    else:
        eList = edges

    for edge in eList:
        for i in range(laneNdict[edge]):
            lanes.append(edge+'_'+str(i))
    return lanes

def getLaneNumbers():
    edges = traci.edge.getIDList()
    lanes = traci.lane.getIDList()
    laneNdict = defaultdict(int)
    for edge in edges:
        for lane in lanes:
            if edge == lane.split('_')[0]:
                laneNdict[edge] += 1
    return laneNdict

def edgeLaneMap():
    eldict = defaultdict(list)
    edges = traci.edge.getIDList()
    lanes = traci.lane.getIDList()
    for edge in edges:
        for lane in lanes:
            if edge == lane.split('_')[0]:
                eldict[edge].append(lane)
    return eldict

def nearRound(x, base):
    fb = float(base)
    return round(float(x)/fb)*fb

def floorRound(x, base):
    fb = float(base)
    return floor(float(x)/fb)*fb

def ceilRound(x, base):
    fb = float(base)
    return ceil(float(x)/fb)*fb

def powerset(iterable, excludeZero=True):
    "powerset([1,2,3]) --> () (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)"
    s = list(iterable)
    if excludeZero:
        return itertools.chain.from_iterable(itertools.combinations(s, r) for r in range(1, len(s)+1))
    else:
        return itertools.chain.from_iterable(itertools.combinations(s, r) for r in range(len(s)+1))

def vehicleSignalParser(traciSignal):
    # converts decimal signal from traci to binary and decodes the bits
    # to their corresponding statuses
    binarySignal = map(int, '{:04d}'.format(int(bin(traciSignal)[2:]))[::-1])
    signalCode = {'BLINKER_RIGHT': binarySignal[0],
                  'BLINKER_LEFT': binarySignal[1],
                  'BLINKER_EMERGENCY': binarySignal[2],
                  'BRAKELIGHT': binarySignal[3]}
    return signalCode

def vehicleSignalParserFull(traciSignal):
    # converts decimal signal from traci to binary and decodes the bits
    # to their corresponding statuses
    binarySignal = map(int, '{:014d}'.format(int(bin(traciSignal)[2:]))[::-1])
    signalCode = {'BLINKER_RIGHT': binarySignal[0],
                  'BLINKER_LEFT': binarySignal[1],
                  'BLINKER_EMERGENCY': binarySignal[2],
                  'BRAKELIGHT': binarySignal[3],
                  'FRONTLIGHT': binarySignal[4],
                  'FOGLIGHT': binarySignal[5],
                  'HIGHBEAM': binarySignal[6],
                  'BACKDRIVE': binarySignal[7],
                  'WIPER': binarySignal[8],
                  'DOOR_OPEN_LEFT': binarySignal[9],
                  'DOOR_OPEN_RIGHT': binarySignal[10],
                  'EMERGENCY_BLUE': binarySignal[11],
                  'EMERGENCY_RED': binarySignal[12],
                  'EMERGENCY_YELLOW': binarySignal[13]}
    return signalCode

def weightedRandomDraw(choices, targetMean, maxits=100000, TOL=False):
    distribution = choices[:]  # copy choices
    # quit early if already converged
    if np.isclose(np.mean(distribution), targetMean):
        return distribution

    # check the calculation can be done
    assert min(choices) <= targetMean, "Min choice out of bound > target"
    assert max(choices) >= targetMean, "Max choice out of bound < target"

    # auto tolerance based on one order of magnitude smaller than least
    # significant number
    if not TOL:
        TOL = 10**-(len(str(targetMean).split('.')[-1]) + 1)
    weightDict = {k: 1 for k in choices}  # make weighting dictionary
    iters = 0  # set initial iteration counter
    mean = targetMean - 100  # set inital mean != target
    # calculate if the distribution mean isn't close to the target mean
    # and we haven't exceeded the iteration limit
    while not np.isclose(mean, targetMean, atol=TOL) and iters < maxits:
        for k in weightDict.keys():
            # if mean too small, add to values that would increase it
            if mean < targetMean and k > mean:
                weightDict[k] += 1
            # if mean too large add to values that would shrink it
            elif mean >= targetMean and k < mean:
                weightDict[k] += 1

            # we could test this after each for loop but we get faster
            # convergence doing it this way (more effort, less iters)
            distribution = []  # new list to write revised distribution into
            for k, v in weightDict.items():
                distribution += [k]*v
            mean = np.mean(distribution)
            if np.isclose(mean, targetMean, atol=TOL):
                break
        iters += 1

    if not np.isclose(mean, targetMean, atol=TOL) or iters == maxits:
        print("WARNING: Result may not have converged!")
    
    return distribution, weightDict
