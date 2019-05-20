# -*- coding: utf-8 -*-
"""
Created on Tue May  8 13:59:50 2018

@author: craig
"""

import pandas as pd
import numpy as np
from numpy.matlib import repmat
from matplotlib import rcParams
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from math import ceil, log10, exp
import sys

def pct(a,b):
    return 100.0*(1.0 - (a/float(b)))

pedStage = True if len(sys.argv) >= 2 else False
pedString = '_ped' if pedStage else ''
models = ['sellyOak_lo', 'sellyOak_avg', 'sellyOak_hi']
controllers = ['GPSVA', 'HVA', 'GPSVAslow']
ctrlMap = {'TRANSYT':'TRANSYT', 'GPSVA':'MATS-FT',
           'GPSVAslow':'MATS-ERR', 'HVA':'MATS-HA'}
selectCols = ['controller','model','run','cvp','routeLength','delay', 'stops']
cvp = np.arange(0,101, 10, dtype=int)
i = 0
for model in models:
    file = 'TRANSYT{}-{}-tripinfo.csv'.format(pedString, model)
    data = pd.read_csv('/hardmem/results/outputCSV/'+file,
                            engine='c', usecols=selectCols)
    data = data[(data.controller == 'TRANSYT') & (data.model == model)]
    data['delay'] = data['delay']/(data['routeLength']*0.001)
    data['stops'] = data['stops']/(data['routeLength']*0.001)
    transytDelay = data.delay.mean()
    transytStops = data.stops.mean() 
    # iterate controllers
    for controller in controllers:
        # subset plot data
        file = '{}{}-{}-tripinfo.csv'.format(controller, pedString, model)
        data = pd.read_csv('/hardmem/results/outputCSV/'+file,
                            engine='c', usecols=selectCols)
        data['delay'] = data['delay']/(data['routeLength']*0.001)
        data['stops'] = data['stops']/(data['routeLength']*0.001)

        for cvp in [10, 50, 100]:
            subset = data[(data.controller == controller) &
                          (data.cvp == cvp) &
                          (data.model == model)]
            ctrlDelay = subset.delay.mean()
            ctrlStops = subset.stops.mean()

            diffDelay = pct(ctrlDelay, transytDelay)
            diffStops = pct(ctrlStops, transytStops)
            print(('{}: {:8} vs. TRANSYT @ {:3d}% CVP: Delay {:3.0f}%, '+\
                   'Stops {:3.0f}%').format(model, ctrlMap[controller], cvp,\
                                            diffDelay, diffStops))
        print('')
        
'''
Crop out legend:
pdfcrop --margins '0 0 0 -600' delay.pdf legend_crop.pdf
pdfcrop --margins '0 0 0 0' legend_crop.pdf legend.pdf
pdftk legend.pdf cat 1 output legend1.pdf
mv legend1.pdf legend.pdf && rm legend_crop.pdf
'''
