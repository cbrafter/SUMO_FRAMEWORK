# -*- coding: utf-8 -*-
"""
Created on Tue May  8 13:59:50 2018

@author: craig
"""

import pandas as pd
import numpy as np
import sys


def pct(a, b):
    return 100.0 * (1.0 - (a / float(b)))


models = ['sellyOak_avg']
emissions = ['CO2', 'CO', 'NOX', 'PMX', 'FUEL']
controllers = ['TRANSYT', 'GPSVA', 'GPSVAslow', 'CDOTS', 'CDOTSslow']
ctrlMap = {'TRANSYT': 'TRANSYT', 'GPSVA': 'MATS',
           'GPSVAslow': 'MATS-ERR', 'HVA': 'MATS-HA',
           'CDOTS': 'CDOTS', 'CDOTSslow': 'CDOTS-ERR'}
pedStage = True
pedString = '_ped' if pedStage else ''
cvp = np.arange(0, 101, 10, dtype=int)
for model in models:
    file = 'TRANSYT{}-{}-emissions.csv'.format(pedString, model)
    tdata = pd.read_csv('/hardmem/results/outputCSV/' + file, engine='c')
    tdata = tdata[(tdata.controller == 'TRANSYT') & (tdata.model == model)]

    for controller in controllers[1:]:
        AA = '-1101000' if 'CDOTS' in controller else ''
        file = '{}{}-{}-emissions.csv'.format(controller,
                                              pedString, model + AA)
        data = pd.read_csv('/hardmem/results/outputCSV/' + file, engine='c')
        data = data[data.cvp.isin([10, 50, 100])]
        for emission in emissions:
            # iterate controllers
            transytEmission = (tdata.groupby(['run'])[emission]
                                    .sum()
                                    .reset_index()[emission]
                                    .mean())

            targetEmission = (data.groupby(['cvp', 'run'])[emission]
                                  .sum()
                                  .reset_index()
                                  .groupby('cvp')[emission]
                                  .mean().values)
            diff = [pct(x, transytEmission) for x in targetEmission]
            print(('{}: {:8} vs. TRANSYT {}: '.format(
                model, ctrlMap[controller], emission) + repr(np.round(diff))))
        print('')
