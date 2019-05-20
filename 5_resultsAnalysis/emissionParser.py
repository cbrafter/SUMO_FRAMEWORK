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


def filtervType(x):
    if 'c_' in x:
        return x.split('_')[1]
    else:
        return x


def parser(fileName):
    controller, model, fileTxt = fileName.split('/')[-3:]
    if '_ped' in controller:
        controller = controller.split('_')[0]
        pedStage = 1
    else:
        pedStage = 0
    run, cvp = [int(x) for x in re.match('.+?R(.+?)_CVP(.+?).csv',
                                         fileTxt).groups()]
    if cvp == 0: print(fileName)
    sys.stdout.flush()
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

# Main script
if len(sys.argv) > 1:
    dataFolder = sys.argv[-1]
else:
    dataFolder = '/hardmem/results/'
outputCSV = dataFolder + 'allEmissionInfo.csv'

# recursive glob using ** notation to expand folders needs python3
resultFiles = glob(dataFolder+'**/**/emission*.csv', recursive=True)
resultFiles.sort()

print('~Parsing Tripfiles~')
# define work pool
nproc = 7
workpool = mp.Pool(processes=nproc)
# Run parsers in parallel
resultData = workpool.map(parser, resultFiles, chunksize=1)
resultData = pd.concat(resultData)
print('Saving data')
resultData.to_csv(outputCSV)
print('~DONE~')
