# -*- coding: utf-8 -*-
"""
Created on Tue May  8 13:59:50 2018

@author: craig
"""

import pandas as pd
import numpy as np
from numpy.matlib import repmat
from math import ceil, log10, exp
from scipy.stats import ttest_ind

data = pd.read_csv('/hardmem/results_test/allTripInfo.csv', engine='c')
data['delay'] = data['delay']/(data['routeLength']*0.001)
data['stops'] = data['stops']/(data['routeLength']*0.001)
#data['PI'] = W*data['delay'] + K*data['stops']
models = ['sellyOak_avg', 'sellyOak_lo', 'sellyOak_hi']
controllers = ['GPSVA', 'GPSVAslow', 'HVA']

cvps = data.cvp.unique()
for model in models:
    for controller in controllers:
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
