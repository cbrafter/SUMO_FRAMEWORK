# -*- coding: utf-8 -*-
"""
Created on Wed Apr 25 12:24:08 2018

@author: craig
"""
import pandas as pd


class freeflowStore(object):
    def __init__(self, fileName=None):
        if fileName is not None:
            self.data = pd.read_csv(fileName)
            # use combined key dictionary for speed
            self.dataDict = {}
            with open(fileName, 'r') as f:
                for line in f:
                    if 'duration' not in line and len(line) > 5:
                        key = ''.join(line.split(',')[:4])
                        value = float(line.split(',')[-1])
                        self.dataDict[key] = value
        else:
            cols = ['type', 'model', 'origin', 'destination',
                    'distance', 'duration']
            self.data = pd.DataFrame(columns=cols)
        # composite key + loc 10x faster than mask, but dict is
        # 10x faster again
        # self.dataMultiKey = self.data.set_index(['type', 'model',
        #                                         'origin', 'destination'])

    def addEntry(self, vType, model, orig, dest, dist, freeflowTime):
        newIndex = len(self.data.index)
        self.data.loc[newIndex] = [vType, model, orig,
                                   dest, dist, freeflowTime]

    def getTime(self, vType, model, orig, dest):
        # vehType = vType if 'c_' not in vType else vType.split('_')[1]
        try:
            # freeflowTime = self.dataMultiKey.loc[(vehType, model,
            # orig, dest),
            #                                     'duration']
            freeflowTime = self.dataDict[vType+model+orig+dest]
            return freeflowTime
        except:
            return None

    def getDistance(self, vType, model, orig, dest):
        vehType = vType if 'c_' not in vType else vType.split('_')[1]
        mask = (self.data.model == model) & (self.data.type == vehType) &\
               (self.data.origin == orig) & (self.data.destination == dest)
        return self.data[mask].distance.tolist()[0]

freeflows = freeflowStore('./freeflows.csv')
