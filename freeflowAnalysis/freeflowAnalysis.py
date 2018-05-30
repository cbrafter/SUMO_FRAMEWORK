# -*- coding: utf-8 -*-
"""
Created on Tue Apr 24 16:31:23 2018

@author: craig
"""
from glob import glob
import pandas as pd
import re
import os


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


files = glob('./results/*.xml')
freeflows = freeflowStore()
regex = '<tripinfo id=.+? departLane="(.+?)_." .+? ' + \
        'arrivalLane="(.+?)_." .+? duration="(.+?)" ' + \
        'routeLength="(.+?)" .+? vType="(.+?)"'
for file in files:
    model = os.path.basename(file).split('_')[0]
    with open(file, 'r') as f:
        for line in f.readlines():
            if '<tripinfo ' in line:
                try:
                    matches = re.match(regex, line.strip()).groups()
                    orig, dest, freeflowTime, dist, vType = matches
                    freeflowTime = float(freeflowTime)
                    dist = float(dist)
                    freeflows.addEntry(vType, model, orig,
                                       dest, dist, freeflowTime)
                except:
                    print(line)
freeflows.data.to_csv('freeflows.csv', index=False)
print('DONE')
