import pandas as pd
import numpy as np
from numpy.matlib import repmat
from math import ceil, log10, exp


def pct(a,b):
    # 100.0-100.0*(a/float(b))
    return 100.0*(1.0 - (a/float(b))

data = pd.read_csv('/hardmem/results_test1/allTripInfo.csv', engine='c')
# data = data[data.model == 'sellyOak_avg']
data['delay'] = data['delay']/(data['routeLength']*0.001)
data['stops'] = data['stops']/(data['routeLength']*0.001)
#data['PI'] = W*data['delay'] + K*data['stops']
models = ['sellyOak_lo', 'sellyOak_avg', 'sellyOak_hi']
controllers = ['GPSVA', 'HVA', 'GPSVAslow']
ctrlMap = {'TRANSYT':'TRANSYT', 'GPSVA':'MATS-FT',
           'GPSVAslow':'MATS-ERR', 'HVA':'MATS-HA'}

subset = data[(data.controller == 'TRANSYT') & (data.model == 'sellyOak_avg')]
transytDelay = subset.delay.mean()
transytStops = subset.stops.mean()

print('Selly Oak Avg, TRANSYT Comparison')
for controller in controllers:
    for cvp in [10, 50, 100]:
        subset = data[(data.controller == controller) &
                      (data.cvp == cvp) &
                      (data.model == 'sellyOak_avg')]
        ctrlDelay = subset.delay.mean()
        ctrlStops = subset.stops.mean()

        diffDelay = pct(ctrlDelay, transytDelay)
        diffStops = pct(ctrlStops, transytStops)
        print(('{:8} vs. TRANSYT @ {:3d}% CVP: Delay {:3.0f}%, '+\
               'Stops {:3.0f}%').format(ctrlMap[controller], cvp,\
                                        diffDelay, diffStops))
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
        
        delay0 = subset0.delay.mean()
        delay100 = subset100.delay.mean()
        stops0 = subset0.stops.mean()
        stops100 = subset100.stops.mean()

        diffDelay = pct(delay100, delay0)
        diffStops = pct(stops100, stops0)
        
        print(('{:12}: {:8} 0% vs. 100% CVP: Delay {:3.0f}%, '+\
               'Stops {:3.0f}%').format(model, ctrlMap[controller],\
                                        diffDelay, diffStops))
    print('')
