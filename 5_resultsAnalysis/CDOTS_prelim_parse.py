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
import traceback


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


def trip_parser(fileName, numeric=False):
    if 'CDOTS' in fileName:
        controller, model, activation, fileTxt = fileName.split('/')[-4:]
    else:
        controller, model, fileTxt = fileName.split('/')[-3:]
    if '_ped' in controller:
        controller = controller.split('_')[0]
        pedStage = True
    else:
        pedStage = False
    try:
        stopDict = getStopInfo(fileName)
    except Exception as e:
        stopDict = defaultdict(lambda: -1)
        # print(fileName, e)
    # print('PARSING: '+fileName)
    sys.stdout.flush()
    run, cvp = [int(x) for x in re.match('.+?R(.+?)_CVP(.+?).xml',
                                         fileTxt).groups()]
    #if cvp == 0: print(fileName)
    regex = '<tripinfo id="(.+?)" depart="(.+?)" departLane="(.+?)" .+? ' + \
            'departDelay="(.+?)" arrival="(.+?)" arrivalLane="(.+?)" ' + \
            '.+? duration="(.+?)" routeLength="(.+?)" .+? ' + \
            'timeLoss="(.+?)" .+? vType="(.+?)" .+?/>'
    regex = re.compile(regex)
    # don't use readlines to save memory
    results = []
    file = open(fileName, 'r')
    for line in file:
        data = regex.match(line.strip())
        if data is None:
            continue
        vID = data.groups()[0]
        data = convertTripData(list(data.groups()[1:])+["1.00"])
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
            # print(ke, controller, model, fileName)
        delay = getDelay(vType, model, origin, destination, journeyTime)
        data = [controller, model, run, cvp, pedStage, depart, origin,
                departDelay, arrival, destination, duration,
                routeLength, timeLoss, vType, speedFactor,
                journeyTime, connected, delay, stops]
        if not numeric:
            data = ','.join(str(x) for x in data) + '\n'
        results.append(data)
    file.close()
    return results


def em_parser(fileName):
    controller, model, fileTxt = fileName.split('/')[-3:]
    if '_ped' in controller:
        controller = controller.split('_')[0]
        pedStage = 1
    else:
        pedStage = 0
    run, cvp = [int(x) for x in re.match('.+?R(.+?)_CVP(.+?).csv',
                                         fileTxt).groups()]

    results = pd.read_csv(fileName, dtype={'vehID':str}, index_col=False)
    results['controller'] = controller
    results['model'] = model
    results['run'] = run
    results['cvp'] = cvp
    results['pedStage'] = pedStage
    results.rename(columns={'type': 'vType'}, inplace=True)
    results['connected'] = results['vType'].apply(lambda x: int('c_' in x))
    results['vType'] =  results['vType'].apply(filtervType)
    return results

if len(sys.argv) > 1:
    dataFolder = sys.argv[-1]
    outputFolder = '/scratch/cbr1g15/hardmem/outputCSV/'
else:
    dataFolder = '/hardmem/results/'
    outputFolder = '/hardmem/results/outputCSV/'

outputFile = outputFolder + 'CDOTSprelim.csv'
# recursive glob using ** notation to expand folders needs python3
tripFiles = glob(dataFolder+'CDOTS*/**/**/trip*')
tripFiles.sort()

# Write ouput file header
with open(outputFile, 'w') as ofile:
    cols = ['controller', 'model', 'run', 'cvp', 'pedStage', "noise",
            "delayMean", "delayStd", "stopsMean", "stopsStd", "activation"]
    ofile.write(','.join(cols) + '\n')

def cdot_parser(tripFile):
    # tripfileheader
    cols = ['controller', 'model', 'run', 'cvp', 'pedStage', "depart", "origin",
            "departDelay", "arrival", "destination", "duration",
            "routeLength", "timeLoss", "vType", "speedFactor",
            "journeyTime", "connected", "delay", "stops"]
    activationArray = ''
    try:
        dirname = os.path.dirname(tripFile)
        if 'CVP000' in tripFile: print('Parsing: '+ dirname)
        noise = 'slow' in dirname
        activationArray = dirname.split('/')[-1]
        emissionFile = re.sub('tripinfo', 'emissions', tripFile)
        emissionFile = re.sub('xml', 'csv', emissionFile)

        tripResults = trip_parser(tripFile, numeric=True)
        tripDF = pd.DataFrame(tripResults, columns=cols)
        # emissionResults = em_parser(emissionFile)

        data = [tripDF.controller[0], tripDF.model[0], tripDF.run[0],
                tripDF.cvp[0], tripDF.pedStage[0], noise,
                tripDF.delay.mean(), tripDF.delay.std(),
                tripDF.stops.mean(), tripDF.stops.std(), activationArray]
        data = ','.join(str(x) for x in data) + '\n'
        return data

    except Exception as e:
        print(str(e))
        traceback.print_exc()

nproc = 7
workpool = mp.Pool(processes=nproc)
resultData = workpool.map(cdot_parser, tripFiles, chunksize=11)
print('Writing data...')
with open(outputFile, 'a') as ofile:
    for result in resultData:
        ofile.write(result)

print('~DONE~')
