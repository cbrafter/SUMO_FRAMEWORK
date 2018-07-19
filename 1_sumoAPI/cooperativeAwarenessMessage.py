# -*- coding: utf-8 -*-
# ETSI CAM Specifications

from math import hypot
import signalTools as sigTools
import traci.constants as tc
import numpy as np

class CAMChannel(object):
    def __init__(self, jcnPosition, jcnCtrlRegion,
                 scanRange=250, CAMoverride=False, PER=0., noise=False):
        self.TGenCamMin = 0.1 # Min time for CAM generation 10Hz/100ms/0.1sec
        self.TGenCamMax = 1.0 # Max time for CAM generation 1Hz/1000ms/1sec
        self.TGenCamDCC = 0.1 # CAM generation time under channel congestion
        self.NGenCamMax = 3
        self.Nsubcarriers = 52 # Num of 802.11p subcarriers
        # Adapt CAM generation based on channel state from ETSI CAM DP2 mode
        self.DCCstate = self.getDCCstate(CAMoverride)
        # linear function for active = lambda x: round(numCAVs*0.0155-0.612, 1)
        # for linear increase in DDC time from 0.9*Nsubcarriers and 3*Nsubcarriers
        # dict[vehID] = [position (x), heading(h), velocity(v), TGenCam(TGC), NGenCam (NGC)]
        # where TGenCam is the time the CAM was generated
        self.transmitData = {} # CAM generated at vehicle T=0
        self.channelData = {} # CAM info in transit T=0.1
        self.receiveData = {} # CAM info at Junction receiver T=0.2

        self.random = np.random.RandomState(1)
        self.PER = PER  # Packet Error Rate
        self.noise = noise  # Bool whether to add noise

        self.scanRange = scanRange
        self.jcnGeometry = (jcnPosition, jcnCtrlRegion)
 
    def getDCCstate(self, CAMoverride = False): 
        return {'RELAXED': CAMoverride if CAMoverride else self.TGenCamMin,
                'ACTIVE': CAMoverride if CAMoverride else 0.2,
                'RESRICTIVE': CAMoverride if CAMoverride else 0.25}

    def setTGenCamDCC(self, Nagents):
        if Nagents <= 0.75*self.Nsubcarriers:
            self.TGenCamDCC = self.DCCstate['RELAXED']
        elif Nagents >= 1.5*self.Nsubcarriers:
            self.TGenCamDCC = self.DCCstate['RESRICTIVE']
        else:
            self.TGenCamDCC = self.DCCstate['ACTIVE']

    def getTGenCam(self, vData, TIME_SEC):
        # Time to Generate CAM
        if vData['NGC'] > self.NGenCamMax:
            return self.TGenCamMax
        else:
            return TIME_SEC - vData['Tgen']

    def channelUpdate(self, vehicleData, TIME_SEC):
        # Receive fata from "channel"
        self.receiveData = self.channelData.copy()
        
        # Set DCC time based on channel state
        numCAVs = len(self.receiveData)
        self.setTGenCamDCC(numCAVs)

        # transmit the last CAMs on the channel
        self.channelData = {}
        chanKeys = self.transmitData.keys()
        RxKeys = self.receiveData.keys()
        for vehID in chanKeys:
            # if packet error do not update channel
            if self.isPktError():
                continue

            # else update channel
            if vehID in RxKeys:
                dx = sigTools.getDistance(self.receiveData[vehID]['pos'],
                                          self.transmitData[vehID]['pos'])
                dh = abs(self.receiveData[vehID]['h'] - self.transmitData[vehID]['h'])
                dv = abs(self.receiveData[vehID]['v'] - self.transmitData[vehID]['v'])
                dt = TIME_SEC - self.receiveData[vehID]['Tgen']
                TGenCam = self.getTGenCam(self.receiveData[vehID], TIME_SEC)
            # No data for this vehicle received yet, force trigger onto channel
            else:
                dx, dh, dv = 5, 5, 1
                dt = TGenCam = self.TGenCamMax + self.TGenCamMin

            # CAM trigger condition 1 data to channel, NGC=0
            # change in: Position change > 4m, heading > 4deg, or speed > 0.5m/s
            if (dx > 4 or dh > 4 or dv > 0.5) and dt >= self.TGenCamDCC:
                self.channelData[vehID] = self.transmitData[vehID].copy()
                self.channelData[vehID]['NGC'] = 0
            # CAM trigger condition 2 - data to channel, NGC++
            elif dt >= self.TGenCamDCC or dt >= TGenCam:
                self.channelData[vehID] = self.transmitData[vehID].copy()
                self.channelData[vehID]['NGC'] += 1
            # No change in CAM information, same as what was previously on channel
            else:
                # self.channelData[vehID] = self.receiveData[vehID].copy()
                # RX = CH so we don't need to copy
                continue

        # Get new data for transmission from the vehicles
        self.transmitData = {}
        compareKeys = self.channelData.keys()
        # check subscription has data
        if vehicleData != None:
            for vehID in vehicleData.keys():
                if tc.VAR_POSITION not in vehicleData[vehID].keys()\
                  or 'c_' not in vehicleData[vehID][tc.VAR_TYPE]:
                    continue
                # check the sub result has vehicle data (not loop data)
                vehPosition = vehicleData[vehID][tc.VAR_POSITION]
                if self.noise:
                    vehPosition = self.addGPSNoise(vehPosition)

                inRange = sigTools.isInRange(vehPosition, self.scanRange,
                                             self.jcnGeometry)
                if inRange:
                    vehHeading = vehicleData[vehID][tc.VAR_ANGLE]
                    if self.noise:
                        vehHeading = self.addHeadingError(vehHeading)
                    vehVelocity = vehicleData[vehID][tc.VAR_SPEED]
                    if vehID in compareKeys:
                        nextNGC = self.channelData[vehID]['NGC']
                    else:
                        nextNGC = 0
                    self.transmitData[vehID] = {'pos': vehPosition,
                                                'h': vehHeading,
                                                'v': vehVelocity,
                                                'Tgen': TIME_SEC,
                                                'NGC': nextNGC}

    def isPktError(self):
        return self.random.random_sample() < self.PER

    def addGPSNoise(self, coord):
        # 99.7% data within 3 sigma (std. dev) 5/3 ~ 1.67
        xerr, yerr = self.random.normal(0, 1.67, 2)
        return coord[0]+xerr, coord[1]+yerr

    def addHeadingError(self, heading):
        return 20*self.random.random_sample() - 10 + heading
