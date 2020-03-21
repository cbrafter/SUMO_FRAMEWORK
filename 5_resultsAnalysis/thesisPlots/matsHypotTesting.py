# -*- coding: utf-8 -*-
"""
Created on Tue May  8 13:59:50 2018

@author: craig
"""

import pandas as pd
import numpy as np
import sys
from numpy.matlib import repmat
from math import ceil, log10, exp
from scipy.stats import ttest_ind

models = ['sellyOak_lo', 'sellyOak_avg', 'sellyOak_hi']
controllers = ['GPSVA', 'GPSVAslow', 'HVA']
pedStage = True if len(sys.argv) >= 2 else False
pedString = '_ped' if pedStage else ''
cvps = np.arange(0,101, 10, dtype=int)
print('DELAY'+pedString)
for model in models:
    for controller in controllers:
        file = '{}{}-{}-tripinfo.csv'.format(controller, pedString, model)
        data = pd.read_csv('/hardmem/results/outputCSV/'+file, engine='c')
        data['delay'] = data['delay']/(data['routeLength']*0.001)
        H0 = data[(data.model == model) &
                  (data.controller == controller) &
                  (data.cvp == cvps[0])]
        for cvp in cvps[1:]:
            H1 = data[(data.model == model) &
                      (data.controller == controller) &
                      (data.cvp == cvp)]
            stat, p = ttest_ind(H0.delay, H1.delay)
            N = np.mean([len(H0.delay), len(H1.delay)])
            print(model, controller, cvp, N, p)
print('\nSTOPS'+pedString)
for model in models:
    for controller in controllers:
        file = '{}{}-{}-tripinfo.csv'.format(controller, pedString, model)
        data = pd.read_csv('/hardmem/results/outputCSV/'+file, engine='c')
        data['stops'] = data['stops']/(data['routeLength']*0.001)
        H0 = data[(data.model == model) &
                  (data.controller == controller) &
                  (data.cvp == cvps[0])]
        for cvp in cvps[1:]:
            H1 = data[(data.model == model) &
                      (data.controller == controller) &
                      (data.cvp == cvp)]
            stat, p = ttest_ind(H0.stops, H1.stops)
            N = np.mean([len(H0.stops), len(H1.stops)])
            print(model, controller, cvp, N, p)
