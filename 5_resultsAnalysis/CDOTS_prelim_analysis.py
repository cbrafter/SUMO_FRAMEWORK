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

fileName = '/hardmem/results/outputCSV/CDOTSprelim.csv'
data = pd.read_csv(fileName)
data['PI'] = 0.25 *((data.delayMean/data.delayMean.max())
                   + (data.delayStd/data.delayStd.max())
                   + (data.stopsMean/data.stopsMean.max())
                   + (data.stopsStd/data.stopsStd.max()))

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
