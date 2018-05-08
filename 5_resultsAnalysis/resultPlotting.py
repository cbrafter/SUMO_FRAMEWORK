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

# Use T1 fonts for plots not bitmap
rcParams['ps.useafm'] = True
rcParams['pdf.use14corefonts'] = True
rcParams['text.usetex'] = True
plt.rcParams["font.family"] = "Times New Roman"
# We're using tex fonts so we need to bolden all text in the preambles not with fontweight='bold'
rcParams['text.latex.preamble'] = [r'\renewcommand{\seriesdefault}{\bfdefault}']

tsize = 20.5
axsize = 20.5
ticksize = 17
nolab = '_nolegend_'


def setsavefig(figure, filepath, dpiVal=300, padding=0.1,
               pdf=True, eps=False, png=False):
    ''' Save figure at publication quality using desired settings
    
    if png:
        figure.savefig(filepath+'.png', dpi=dpiVal,
                       bbox_inches='tight', pad_inches=padding)
    if eps:
        figure.savefig(filepath+'.eps', dpi=dpiVal,
                       bbox_extra_artists=(lgnd,),
                       bbox_inches='tight', pad_inches=padding)
    '''
    if pdf:
        figure.savefig(filepath+'.pdf', dpi=dpiVal,
                       # bbox_extra_artists=(lgnd,),
                       bbox_inches='tight', pad_inches=padding)


def plotPercentile(data, scale, style='k-', alpha_val=1):
    if len(data.shape) == 1:
        bands = np.percentile(data, [5, 95], axis=0)
        bands = repmat(bands, scale.shape[0], 1).T
    elif len(data.shape) == 2:
        bands = np.percentile(data, [5, 95], axis=0)
    else:
        print('This data is not a vector/2D-Matrix!')

    xerr = bands[0, :]
    yerr = bands[1, :]
    return xerr, yerr

lineStyle = {'VA': '^k',
             'fixedTime': 'vC7',
             'GPSVA': '*C2',
             'HVA': 'oC3'}

data = pd.read_csv('/hardmem/results_test/allTripInfo.csv')
models = ['sellyOak_avg', 'sellyOak_hi', 'sellyOak_lo']
controllers = ['fixedTime', 'GPSVA']

# plot sellyOak results
fig = plt.figure(figsize=(16, 9))
lines = []
labels = []
cvp = data.groupby('cvp').delay.mean().index.values
i=0
for model in models:
    fig = plt.figure(figsize=(16, 9))
    lines = []
    labels = []
    cvp = data.groupby('cvp').delay.mean().index.values
    for controller in controllers:
        if model=='sellyOak_hi' and controller == 'GPSVA':
            continue
        
        plotData = data[(data.model == model) &
                        (data.controller == controller)]
        meanDelay = plotData.groupby('cvp').delay.mean().values
        err = plotData.groupby('cvp')\
                      .delay\
                      .apply(lambda x: np.percentile(x, [5, 95]))\
                      .values
        err = np.array([[lo, hi] for lo, hi in err])
        if controller in ['VA', 'fixedTime']:
            meanDelay = meanDelay * np.ones_like(cvp)
            err = err * np.ones_like(cvp[:, np.newaxis])

        lines.append(plt.errorbar(cvp, meanDelay, 
                                  yerr=[meanDelay-err[:, 1],
                                        err[:, 0]-meanDelay], 
                                  fmt=lineStyle[controller]+'-', 
                                  linewidth=2, markersize=10,
                                  label=controller, 
                                  capsize=7, capthick=2, elinewidth=1))
        labels.append(controller)
        #plt.title(model+': Delay vs. CV Penetration', fontsize=tsize)
        plt.xlabel('Percentage CV Penetration', fontsize=axsize, fontweight='bold')
        plt.ylabel('Delay [s]', fontsize=axsize)
        plt.ylim([0,1000])
    setsavefig(fig, './delay'+str(i))
    i+=1







