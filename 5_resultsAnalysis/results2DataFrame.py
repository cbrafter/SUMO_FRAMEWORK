# -*- coding: utf-8 -*-
"""
Created on Thu May  3 09:52:21 2018

@author: craig
"""

import re
from glob import glob
import multiprocessing as mp
from freeflows import freeflows
import sys
import os
from collections import defaultdict
import pandas as pd


def convertTripData(data):
    newData = []
    for i, x in enumerate(data):
        if i in [0, 2, 3, 5, 6, 7, 9]:
            newData.append(float(x))
        else:
            newData.append(x)
    return newData


def filtervType(x):
    if 'c_' in x:
        return x.split('_')[1]
    else:
        return x


def getDelay(vType, netModel, origin, destination, journeyTime):
    try:
        model = netModel.split('_')[0]
        freeflowTime = freeflows.getTime(vType, model,
                                         origin, destination)
        assert freeflowTime is not None
        assert freeflowTime > -1.0
        return abs(journeyTime - freeflowTime)
    except:
        return -1


def getStopInfo(fname):
    path, file = os.path.split(fname)
    stopfile = re.sub('tripinfo', 'stops', file)
    stopfile = re.sub('xml', 'csv', stopfile)
    stopfile = os.path.join(path, stopfile)
    df = pd.read_csv(stopfile, dtype={'vehID':str, 'stops':int})
    df.set_index('vehID', inplace=True)
    return defaultdict(int, df.to_dict()['stops'])


def parser(fileName):
    controller, model, fileTxt = fileName.split('/')[-3:]
    try:
        stopDict = getStopInfo(fileName)
    except Exception as e:
        stopDict = defaultdict(lambda: -1)
        print(fileName, e)

    # print('PARSING: '+fileName)
    sys.stdout.flush()
    run, cvp = [int(x) for x in re.match('.+?R(.+?)_CVP(.+?).xml',
                                         fileTxt).groups()]

    regex = '<tripinfo id="(.+?)" depart="(.+?)" departLane="(.+?)" .+? ' + \
            'departDelay="(.+?)" arrival="(.+?)" arrivalLane="(.+?)" ' + \
            '.+? duration="(.+?)" routeLength="(.+?)" .+? ' + \
            'timeLoss="(.+?)" .+? vType="(.+?)" speedFactor="(.+?)" .+?/>'
    regex = re.compile(regex)
    # don't use readlines to save memory
    results = []
    file = open(fileName, 'r')
    for line in file:
        data = regex.match(line.strip())
        if data is None:
            continue
        vID = data.groups()[0]
        data = convertTripData(data.groups()[1:])
        depart, origin, departDelay, arrival, destination,\
            duration, routeLength, timeLoss, vType,\
            speedFactor = data
        # total journey time
        journeyTime = duration + departDelay
        # bool for if vehicle connected or not
        connected = int('c_' in vType)
        # remove connectivity indicator from vType
        vType = filtervType(vType)
        # only edge id for origin and destination
        origin = origin.split('_')[0]
        destination = destination.split('_')[0]
        # calculate delay
        try:
            stops = stopDict[vID]
        except KeyError as ke:
            stops = -1
            print(ke, controller, model, fileName)
        delay = getDelay(vType, model, origin, destination, journeyTime)
        data = [controller, model, run, cvp, depart, origin,
                departDelay, arrival, destination, duration,
                routeLength, timeLoss, vType, speedFactor,
                journeyTime, connected, delay, stops]
        data = ','.join(str(x) for x in data) + '\n'
        results.append(data)
    file.close()
    return results

dataFolder = '/hardmem/results_test/'
outputCSV = dataFolder + 'allTripInfo.csv'

# recursive glob using ** notation to expand folders needs python3
# resultFiles = glob(dataFolder+'**/tripinfo*.xml', recursive=True)
resultFiles = glob(dataFolder+'fixedTime/**/tripinfo*.xml', recursive=True)
resultFiles += glob(dataFolder+'HVA/**/tripinfo*.xml', recursive=True)
resultFiles += glob(dataFolder+'HVAslow/**/tripinfo*.xml', recursive=True)
resultFiles += glob(dataFolder+'GPSVA/**/tripinfo*.xml', recursive=True)
resultFiles += glob(dataFolder+'GPSVAslow/**/tripinfo*.xml', recursive=True)
resultFiles.sort()
# resultFiles = [x for x in resultFiles if 'GPSVA/sellyOak_hi' not in x]
print('~Parsing Tripfiles~')
# define work pool
nproc = 4
workpool = mp.Pool(processes=nproc)
# Run parsers in parallel
resultData = workpool.map(parser, resultFiles, chunksize=1)
resultData = [line for file in resultData for line in file]

print('Saving data')
with open(outputCSV, 'w') as ofile:
    cols = ['controller', 'model', 'run', 'cvp', "depart", "origin",
            "departDelay", "arrival", "destination", "duration",
            "routeLength", "timeLoss", "vType", "speedFactor",
            "journeyTime", "connected", "delay", "stops"]
    ofile.write(','.join(cols) + '\n')
    for line in resultData:
        ofile.write(line)

print('~DONE~')
