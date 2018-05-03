# -*- coding: utf-8 -*-
"""
Created on Thu May  3 09:52:21 2018

@author: craig
"""

import pandas as pd
import re
from glob import glob
import multiprocessing as mp
from freeflows import freeflows
import sys

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


def getDelay(x):
    freeflowTime = freeflows.getTime(x['vType'], x['model'],
                                     x['origin'], x['destination'])
    return abs(x['journeyTime'] - freeflowTime)


def parser(fileName):
    controller, model, fileTxt = fileName.split('/')[-3:]
    print('PARSING: '+fileTxt)
    sys.stdout.flush()
    run, cvp = [int(x) for x in re.match('.+?R(.+?)_CVP(.+?).xml',
                                         fileTxt).groups()]

    regex = '<tripinfo .+? depart="(.+?)" departLane="(.+?)" .+? ' + \
            'departDelay="(.+?)" arrival="(.+?)" arrivalLane="(.+?)" ' + \
            '.+? duration="(.+?)" routeLength="(.+?)" .+? ' + \
            'timeLoss="(.+?)" .+? vType="(.+?)" speedFactor="(.+?)" .+?/>'
    regex = re.compile(regex)

    cols = ['controller', 'model', 'run', 'cvp', "depart", "origin",
            "departDelay", "arrival", "destination", "duration",
            "routeLength", "timeLoss", "vType", "speedFactor"]
    df = pd.DataFrame(columns=cols)
    file = open(fileName, 'r')

    # don't use readlines to save memory
    for line in file:
        if '<tripinfo ' in line:
            data = regex.match(line.strip()).groups()
            data = convertTripData(data)
            df.loc[len(df.index)] = [controller, model, run, cvp] + data
    file.close()
    return df

dataFolder = '/hardmem/results_test/'
outputCSV = dataFolder + 'allTripInfo.csv'

# recursive glob using ** notation to expand folders
resultFiles = glob(dataFolder+'**/*.xml', recursive=True)
resultFiles.sort()

print('~Parsing Tripfiles~')
# define work pool
nproc = 8
workpool = mp.Pool(processes=nproc)
# Run simualtions in parallel
resultDFs = workpool.map(parser, resultFiles, chunksize=1)
allData = pd.concat(resultDFs, ignore_index=True)
resultDFs = 0  # dereference to save memory
print('Calculating new columns')

# calculate delay
allData['journeyTime'] = allData['duration'] + allData['departDelay']
# determine if vehicle connected or not and remove appending 'c_'
allData['connected'] = allData['vType'].apply(lambda x: int('c_' in x))
allData['vType'] = allData['vType'].apply(filtervType)

# remove lane number from origin and destination
allData['origin'] = allData['origin'].apply(lambda x: x.split('_')[0])
allData['destination'] = allData['destination'].apply(lambda x:
                                                      x.split('_')[0])
# get freeFlow time
allData['delay'] = allData.apply(getDelay, axis=1)

print('Saving data')
allData.to_csv(outputCSV, index=False)
print('~DONE~')
