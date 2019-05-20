import pandas as pd
import numpy as np
from numpy.matlib import repmat
from math import ceil, log10, exp


def pct(a,b):
    return 100.0-100.0*(a/float(b))

data = pd.read_csv('/hardmem/results_test1/allEmissionInfo.csv', engine='c')

models = ['sellyOak_lo', 'sellyOak_avg', 'sellyOak_hi']
controllers = ['GPSVA', 'HVA', 'GPSVAslow']
ctrlMap = {'TRANSYT':'TRANSYT', 'GPSVA':'MATS-FT',
           'GPSVAslow':'MATS-ERR', 'HVA':'MATS-HA'}
emissions = ['CO2', 'CO', 'PMX', 'NOX', 'FUEL']

subset = data[(data.controller == 'TRANSYT') & (data.model == 'sellyOak_avg')]
transytEmissions = subset.sum()


for em in emissions:
    print('***Emission: '+em)
    print('Selly Oak Avg, TRANSYT Comparison')
    for controller in controllers:
        for cvp in [10, 50, 100]:
            subset = data[(data.controller == controller) &
                          (data.cvp == cvp) & 
                          (data.model == 'sellyOak_avg')]
            totEmission = subset[em].sum()

            diffEmission = pct(totEmission, transytEmissions)
            print('{:8} vs. TRANSYT @ {:3d}% CVP: Emission Diff {:3.0f}%'\
                .format(ctrlMap[controller], cvp, diffEmission))
        print('')

    print('\nAll demand, all controller 0 vs 100% Comparison')
    for model in models:
        for controller in controllers:
            subset0 = data[(data.controller == controller) &
                           (data.cvp == 0) &
                           (data.model == model)]
            subset100 = data[(data.controller == controller) &
                           (data.cvp == 100) &
                           (data.model == model)]
            
            totEmission0 = subset0[em].sum()
            totEmission100 = subset100[em].sum()

            diffEmission = pct(delay100, delay0)
            
            print('{:12}: {:8} 0% vs. 100% CVP: Emission Diff {:3.0f}%'\
                .format(model, ctrlMap[controller], diffEmission))
        print('')
    print('************************************************************\n')
