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

# Use T1 fonts for plots not bitmap
rcParams['ps.useafm'] = True
rcParams['pdf.use14corefonts'] = True
rcParams['text.usetex'] = True
plt.rcParams["font.family"] = "Times New Roman"
# We're using tex fonts so we need to bolden all text in the preambles
# not with fontweight='bold'
rcParams['text.latex.preamble'] = \
    [r'\renewcommand{\seriesdefault}{\bfdefault}']

tsize = 30
axsize = 29
ticksize = 29
nolab = '_nolegend_'


def roundUp(x, num):
    return int(ceil(x/float(num)))*int(num)


def savePDF(pdfFile, figure):
    ''' Save figure at publication quality using desired settings
    '''
    pdfFile.savefig(figure, dpi=600,
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
             'TRANSYT': 'vC7',
             'GPSVA': '*C2',
             'HVA': 'oC3'}

data = pd.read_csv('/hardmem/results_test/allTripInfo.csv', engine='c')
W = 1.0  # delay cost per second
K = 14.0  # cost per stop time to decel + time to accel for car
#data['delay'] = data['delay']/(data['routeLength']*0.001)
data['stops'] = data['stops']/(data['routeLength']*0.001)
#data['PI'] = W*data['delay'] + K*data['stops']
models = ['sellyOak_avg', 'sellyOak_lo', 'sellyOak_hi']
modMap = {'sellyOak_avg':'Selly Oak Avg.',
          'sellyOak_lo':'Selly Oak Low',
          'sellyOak_hi':'Selly Oak High',
          'twinT': 'Twin-T','cross':'cross'}
controllers = ['TRANSYT', 'GPSVA', 'GPSVAslow', 'HVA']
ctrlMap = {'TRANSYT':'TRANSYT', 'GPSVA':'MATS-FT',
           'GPSVAslow':'MATS-ERR', 'HVA':'MATS-HA'}
figuresPDF = PdfPages('stops.pdf')

def errBands(delay):
    # 90% travel-time/delay confidence interval
    logDelay = np.log(delay)
    mu = np.mean(logDelay)
    sigma = np.std(logDelay)
    z = 1.96
    a = 0.05
    za = z*a
    lowerCI = exp(mu - (za/2.0*sigma))
    upperCI = exp(mu + (za/2.0*sigma))
    return [lowerCI, upperCI]

cvp = data.cvp.unique()
i = 0

yMaxDict = {'sellyOak_hi': 11, 'sellyOak_lo': 4.5, 'sellyOak_avg':5.5}
yMaxDict = {'sellyOak_hi': 26, 'sellyOak_lo': 6, 'sellyOak_avg':12}
for model in models:
    fig = plt.figure(figsize=(16, 9))  # set figure size
    lines = []
    labels = []
    # iterate controllers
    for controller in controllers:
        if 'avg' not in model and controller == 'TRANSYT':
            continue 
        # subset plot data
        plotData = data[(data.model == model) &
                        (data.controller == controller)]
        
        # if no data in this set continue
        if plotData.empty:
            print('{} {} *NULL*'.format(model, controller))
            continue
        
        # get mean delay across all runs
        meanDelay = plotData.groupby('cvp').stops.mean().values
        
        # get error limits 
        err = plotData.groupby('cvp')\
                      .stops\
                      .apply(lambda x: np.percentile(x, [10, 90]))\
                      .values
        err = np.array([[lo, hi] for lo, hi in err])
        if controller in ['VA', 'TRANSYT']:
            meanDelay = meanDelay * np.ones_like(cvp)
            fixedMax = meanDelay[0]
            err = err * np.ones_like(cvp[:, np.newaxis])
        errLims = [meanDelay-err[:, 1], err[:, 0]-meanDelay]
        lines.append(plt.errorbar(cvp, meanDelay,
                                  yerr=errLims,
                                  fmt=lineStyle[controller]+'-',
                                  linewidth=2, markersize=12,
                                  label=controller,
                                  capsize=9, capthick=3, elinewidth=1))
        print(model, controller, meanDelay[-1])
        # plt.fill_between(cvp, err[:, 1], err[:, 0],
        #                  color=lineStyle[controller][1:], alpha=0.3)
        labels.append(ctrlMap[controller])
        modName = modMap[model]
        plt.title(modName+': Stops vs. CV Penetration', fontsize=tsize)
        plt.xlabel('Percentage CV Penetration', fontsize=axsize,
                   fontweight='bold')
        plt.ylabel('Stops [stops/km]', fontsize=axsize)
        # order of magnitude of the max point
        # set x and y lims with some space around the max and min values
        plt.xticks(cvp, fontsize=ticksize, fontweight='bold')
        maxVal = max([min(l[1][0].get_ydata()[:2]) for l in lines])
        if yMaxDict[model] < 10:
            magnitude = 1
        elif yMaxDict[model] > 20:
            magnitude = 4
        else:
            magnitude = 2
        yMax = ceil(maxVal)
        # double the ytick interval
        newYticks = np.arange(0, yMaxDict[model]+1, 0.5*magnitude, dtype=float)
        plt.yticks(newYticks, fontsize=ticksize, fontweight='bold')
        yMin = -0.1
        plt.ylim([yMin, yMaxDict[model]])
        plt.xlim([-3, 103])
        #plt.legend(labels, prop={'size': ticksize-2}, labelspacing=1,
        #    loc='upper center', bbox_to_anchor=(0.5, 1.15), ncol=4)
    savePDF(figuresPDF, fig)
    i += 1

figuresPDF.close()

'''
Crop out legend:
pdfcrop --margins '0 0 0 -600' legend.pdf legend_crop.pdf
pdfcrop --margins '0 0 0 0' legend_crop.pdf legend.pdf
pdftk legend.pdf cat 1 output legend1.pdf
mv legend1.pdf legend.pdf && rm legend_crop.pdf
'''
