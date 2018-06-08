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
from math import ceil, log10

# Use T1 fonts for plots not bitmap
rcParams['ps.useafm'] = True
rcParams['pdf.use14corefonts'] = True
rcParams['text.usetex'] = True
plt.rcParams["font.family"] = "Times New Roman"
# We're using tex fonts so we need to bolden all text in the preambles
# not with fontweight='bold'
rcParams['text.latex.preamble'] = \
    [r'\renewcommand{\seriesdefault}{\bfdefault}']

tsize = 21
axsize = 20
ticksize = 20
nolab = '_nolegend_'


def roundUp(x, num):
    return int(ceil(x/float(num)))*int(num)


def savePDF(pdfFile, figure):
    ''' Save figure at publication quality using desired settings
    '''
    pdfFile.savefig(figure, dpi=300,
                    # bbox_extra_artists=(lgnd,),
                    bbox_inches='tight', pad_inches=0.1)


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

lineStyle = {'GPSVAslow': '^k',
             'fixedTime': 'vC7',
             'GPSVA': '*C2',
             'HVA': 'oC3'}

data = pd.read_csv('/hardmem/results_test/allTripInfo.csv')
W = 1.0  # delay cost per second
K = 14.0  # cost per stop time to decel + time to accel for car
#data['delay'] = data['delay']/(data['routeLength']*0.001)
#data['stops'] = data['stops']/(data['routeLength']*0.001)
data['PI'] = W*data['delay'] + K*data['stops']
models = ['sellyOak_avg', 'sellyOak_lo', 'sellyOak_hi']
modMap = {'sellyOak_avg':'Selly Oak Avg.',
          'sellyOak_lo':'Selly Oak Low',
          'sellyOak_hi':'Selly Oak High'}
controllers = ['fixedTime', 'HVA']
figuresPDF = PdfPages('figures.pdf')

# plot sellyOak results
cvp = data.groupby('cvp').delay.mean().index.values
i = 0
for model in models:
    fig = plt.figure(figsize=(16, 9))
    lines = []
    labels = []
    for controller in controllers+['GPSVA', 'GPSVAslow']:
        if controller in ['GPSVA', 'HVAslow', 'GPSVAslow'] and model != 'sellyOak_avg': continue
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
            fixedMax = meanDelay[0]
            err = err * np.ones_like(cvp[:, np.newaxis])
        errLims = [meanDelay-err[:, 1], err[:, 0]-meanDelay]
        lines.append(plt.errorbar(cvp, meanDelay,
                                  yerr=errLims,
                                  fmt=lineStyle[controller]+'-',
                                  linewidth=2, markersize=10,
                                  label=controller,
                                  capsize=7, capthick=2, elinewidth=1))
        print(model, controller, meanDelay[-1])
        # plt.fill_between(cvp, err[:, 1], err[:, 0],
        #                  color=lineStyle[controller][1:], alpha=0.3)
        labels.append(controller)
        modName = modMap[model]
        plt.title(modName+': Delay vs. CV Penetration', fontsize=tsize)
        plt.xlabel('Percentage CV Penetration', fontsize=axsize,
                   fontweight='bold')
        plt.ylabel('Delay [s]', fontsize=axsize)
        # order of magnitude of the max point
        # set x and y lims with some space around the max and min values
        plt.xticks(cvp, fontsize=ticksize, fontweight='bold')
        maxVal = max([l[1][0].get_ydata()[1] for l in lines])
        magnitude = 10**int(log10(maxVal))
        yMax = roundUp(maxVal, 0.5*magnitude)
        # double the ytick interval
        if magnitude < 10000:
            newYticks = np.arange(0, yMax+1, 0.5*magnitude, dtype=int)
        else:
            newYticks = np.arange(0, yMax+1, 0.5*magnitude, dtype=int)
        plt.yticks(newYticks, fontsize=ticksize, fontweight='bold')
        yMin = -0.5*newYticks[1]
        plt.ylim([yMin, yMax])
        plt.xlim([-3, 103])
        plt.legend(labels, prop={'size': ticksize-2}, labelspacing=1, loc='upper right')
    savePDF(figuresPDF, fig)
    i += 1

i = 0
for model in models:
    if model != 'sellyOak_hi': continue
    fig = plt.figure(figsize=(16, 9))
    lines = []
    labels = []
    for controller in controllers:
        plotData = data[(data.model == model) &
                        (data.controller == controller)]
        meanDelay = plotData.groupby('cvp').PI.sum().values

        if controller in ['VA', 'fixedTime']:
            meanDelay = meanDelay * np.ones_like(cvp)
        meanDelay = meanDelay[1:]
        lines.append(plt.errorbar(cvp[1:], meanDelay,
                                  fmt=lineStyle[controller]+'-',
                                  linewidth=2, markersize=10,
                                  label=controller,
                                  capsize=7, capthick=2, elinewidth=1))
        print(model, controller, meanDelay[-1])

        labels.append(controller)
        modName = modMap[model]
        plt.title(modName+': TRANSYT PI vs. CV Penetration', fontsize=tsize)
        plt.xlabel('Percentage CV Penetration', fontsize=axsize,
                   fontweight='bold')
        plt.ylabel('TRANSYT PI', fontsize=axsize)
        # order of magnitude of the max point
        # set x and y lims with some space around the max and min values
        plt.xticks(cvp[1:], fontsize=ticksize, fontweight='bold')
        maxVal = max([l[0].get_ydata()[0] for l in lines])
        magnitude = 10**int(log10(maxVal))
        yMax = roundUp(maxVal, 0.5*magnitude)
        # double the ytick interval
        if magnitude < 10000:
            newYticks = np.arange(0, yMax+1, 0.5*magnitude, dtype=int)
        else:
            newYticks = np.arange(0, yMax+1, 0.5*magnitude, dtype=int)
        plt.yticks(newYticks, fontsize=ticksize, fontweight='bold')
        yMin = -0.5*newYticks[1]
        plt.ylim([yMin, yMax])
        plt.xlim([7, 103])
        plt.legend(labels, prop={'size': ticksize-2}, labelspacing=1, loc='center right')
    savePDF(figuresPDF, fig)
    i += 1

i = 0
for model in models:
    if model == 'sellyOak_hi': continue
    fig = plt.figure(figsize=(16, 9))
    lines = []
    labels = []
    for controller in controllers+['GPSVA', 'GPSVAslow']:
        if controller in ['GPSVA', 'HVAslow', 'GPSVAslow'] and model != 'sellyOak_avg': continue
        plotData = data[(data.model == model) &
                        (data.controller == controller)]
        meanDelay = plotData.groupby('cvp').PI.sum().values

        if controller in ['VA', 'fixedTime']:
            meanDelay = meanDelay * np.ones_like(cvp)
        meanDelay = meanDelay[1:]
        lines.append(plt.errorbar(cvp[1:], meanDelay,
                                  fmt=lineStyle[controller]+'-',
                                  linewidth=2, markersize=10,
                                  label=controller,
                                  capsize=7, capthick=2, elinewidth=1))
        print(model, controller, meanDelay[-1])

        labels.append(controller)
        modName = modMap[model]
        plt.title(modName+': TRANSYT PI vs. CV Penetration', fontsize=tsize)
        plt.xlabel('Percentage CV Penetration', fontsize=axsize,
                   fontweight='bold')
        plt.ylabel('TRANSYT PI', fontsize=axsize)
        # order of magnitude of the max point
        # set x and y lims with some space around the max and min values
        plt.xticks(cvp[1:], fontsize=ticksize, fontweight='bold')
        maxVal = max([l[0].get_ydata()[0] for l in lines])
        magnitude = 10**int(log10(maxVal))
        yMax = roundUp(maxVal, 0.5*magnitude)
        # double the ytick interval
        if magnitude < 10000:
            newYticks = np.arange(0, yMax+1, 0.5*magnitude, dtype=int)
        else:
            newYticks = np.arange(0, yMax+1, 0.5*magnitude, dtype=int)
        plt.yticks(newYticks, fontsize=ticksize, fontweight='bold')
        yMin = -0.5*newYticks[1]
        plt.ylim([yMin, yMax])
        plt.xlim([7, 103])
        plt.legend(labels, prop={'size': ticksize-2}, labelspacing=1, loc='lower right')
    savePDF(figuresPDF, fig)
    i += 1

figuresPDF.close()

'''
from scipy.stats import ttest_ind
x = plotData
for n in range(2,10):
    d1 = x[x.run.isin(list(range(1,n)))].groupby('cvp').delay.mean().values
    d2 = x[x.run.isin(list(range(1,n+1)))].groupby('cvp').delay.mean().values
    t, p = ttest_ind(d1, d2)
    print(n, t, 1-p)
'''
