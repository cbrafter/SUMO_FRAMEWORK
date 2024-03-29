import re
from glob import glob
import multiprocessing as mp
from freeflows import freeflows
import sys
import os
from collections import defaultdict
import pandas as pd
import traceback
import numpy as np

fileName = '/hardmem/results/CDOTSprelim.csv'
data = pd.read_csv(fileName)
# data['PI'] = 0.25 *((data.delayMean/data.delayMean.max())
#                    + (data.delayStd/data.delayStd.max())
#                    + (data.stopsMean/data.stopsMean.max())
#                    + (data.stopsStd/data.stopsStd.max()))
data['PI'] = 0.5 *((data.delayMean/data.delayMean.max())
                   + (data.stopsMean/data.stopsMean.max()))

for controller in data.controller.unique():
    totalArrays = 0
    bitCounter = [0]*8
    ranks = []
    print(controller)
    for cvp in data.cvp.unique():
        subset = data[(data.controller == controller) & (data.cvp == cvp)]
        ranks.append(subset.sort_values('PI').head(20).activation.values)
    for rankList in ranks:
        for rank in rankList:
            totalArrays += 1
            if not rank%2:
                for i, bit in enumerate(str(rank)):
                    bitCounter[i] += int(bit)
    print(bitCounter)
    print(np.array(bitCounter).argsort()[::-1])
    for rank in ranks[-1]:
        count = 0
        # ignore 0 pct as no difference, and not 100 %
        for rankList in ranks[1:-1]:
            if rank in rankList:
                count += 1
        if count == (len(ranks) - 2) and rank%2:
            print(rank)


for controller in data.controller.unique():
    totalArrays = 0
    bitCounter = [0]*8
    ranks = []
    print(controller)
    for cvp in data.cvp.unique():
        #print(controller, cvp)
        subset = data[(data.controller == controller) & (data.cvp == cvp)]
        subset = subset[subset.activation.apply(lambda x: True if not x%2 else False)]
        ranks.append(subset.sort_values('PI').head(10).activation.values)
        for rankList in ranks:
            for rank in rankList:
                totalArrays += 1
                if not rank%2:
                    for i, bit in enumerate(str(rank)):
                        bitCounter[i] += int(bit)
        sortargs = np.array(bitCounter).argsort()[::-1]
        bestArray = np.zeros_like(sortargs)
        bestArray[sortargs[:4]] = 1
        print(list(bestArray), cvp)
        #print(list(sortargs), cvp)


for i in range(0,101,10):
    subset = data[(data.controller=='CDOTSslow')&(data.cvp==i)]
    print subset[subset.PI==subset.PI.max()].delayMean.values[0] - subset[subset.PI==subset.PI.min()].delayMean.values[0]
subset.sort_values('PI').head()
subset.sort_values('PI').tail()

# Mean data srcs in top 10 
subset = data[(data.controller=='CDOTS')&(data.cvp==100)]
subset.sort_values('PI').head(10).activation.apply(lambda x: str(x).count('1')).mean()
