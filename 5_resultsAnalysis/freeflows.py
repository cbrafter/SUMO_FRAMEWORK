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
        else:
            cols = ['type', 'model', 'origin', 'destination',
                    'distance', 'duration']
            self.data = pd.DataFrame(columns=cols)


    def addEntry(self, vType, model, orig, dest, dist, freeflowTime):
        newIndex = len(self.data.index)
        self.data.loc[newIndex] = [vType, model, orig,
                                   dest, dist, freeflowTime]

    def getTime(self, vType, model, orig, dest):
        vehType = vType if 'c_' not in vType else vType.split('_')[1]
        mask = (self.data.model == model) & (self.data.type == vehType) &\
               (self.data.origin == orig) & (self.data.destination == dest)
        freeflowTime = self.data[mask].duration.tolist()
        if len(freeflowTime) == 0:
            raise ValueError('ValueError: failed on {}'.format([vehType, model, orig, dest])) 
        return freeflowTime[0]

    def getDistance(self, vType, model, orig, dest):
        vehType = vType if 'c_' not in vType else vType.split('_')[1]
        mask = (self.data.model == model) & (self.data.type == vehType) &\
               (self.data.origin == orig) & (self.data.destination == dest)
        return self.data[mask].distance.tolist()[0]

freeflows = freeflowStore('./freeflows.csv')
