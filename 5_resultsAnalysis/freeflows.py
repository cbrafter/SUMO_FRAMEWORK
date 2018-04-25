# -*- coding: utf-8 -*-
"""
Created on Wed Apr 25 12:24:08 2018

@author: craig
"""
import pandas as pd


class freeflowStore(object):
    def __init__(self):
        cols = ['type', 'model', 'origin', 'destination',
                'distance', 'duration']
        self.data = pd.DataFrame(columns=cols)

    def addEntry(self, vType, model, orig, dest, dist, freeflowTime):
        newIndex = len(self.data.index)
        self.data.loc[newIndex] = [vType, model, orig,
                                   dest, dist, freeflowTime]

    def getTime(self, vType, model, orig, dest):
        mask = (self.data.model == model) & (self.data.type == vType) &\
               (self.data.origin == orig) & (self.data.destination == dest)
        return self.data[mask].duration.tolist()[0]

    def getDistance(self, vType, model, orig, dest):
        mask = (self.data.model == model) & (self.data.type == vType) &\
               (self.data.origin == orig) & (self.data.destination == dest)
        return self.data[mask].distance.tolist()[0]

freeflows = pd.read_csv('./freeflows.csv')
