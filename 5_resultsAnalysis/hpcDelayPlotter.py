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

models = ['sellyOak_avg', 'sellyOak_lo', 'sellyOak_hi']
modMap = {'sellyOak_avg':'Selly Oak Avg.',
          'sellyOak_lo':'Selly Oak Low',
          'sellyOak_hi':'Selly Oak High',
          'twinT': 'Twin-T','cross':'cross'}
controllers = ['TRANSYT', 'GPSVA', 'GPSVAslow', 'HVA']
ctrlMap = {'TRANSYT':'TRANSYT', 'GPSVA':'MATS-FT',
           'GPSVAslow':'MATS-ERR', 'HVA':'MATS-HA'}

pedStage = True if len(sys.argv) >= 2 else False
pedString = '_ped' if pedStage else ''
pdfFileName = 'delay{}.pdf'.format(pedString)
figuresPDF = PdfPages(pdfFileName)
print('Writing: '+pdfFileName)

# only store the cols we need to save memory
selectCols = ['controller','model','run','cvp','routeLength','delay']
cvp = np.arange(0,101, 10, dtype=int)
i = 0
for model in models:
    fig = plt.figure(figsize=(16, 9))  # set figure size
    lines = []
    labels = []
    # iterate controllers
    for controller in controllers:
        # subset plot data
        file = '{}{}-{}-tripinfo.csv'.format(controller, pedString, model)
        data = pd.read_csv('/hardmem/results/outputCSV/'+file,
                            engine='c', usecols=selectCols)
        data['delay'] = data['delay']/(data['routeLength']*0.001)    
        # if no data in this set continue
        if data.empty:
            print('{} {} *NULL*'.format(model, controller))
            continue
        else:
            data = data.groupby('cvp').delay
            # Distribution of means
            # data = (data.groupby(['cvp', 'run'])['delay']
            #                       .mean()
            #                       .reset_index()
            #                       .groupby('cvp')['delay'])
        
        # get mean delay across all runs
        meanDelay = data.mean().values
        
        # get error limits 
        err = data.apply(lambda x: np.percentile(x, [10, 90])).values
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
    plt.title(modName+': Delay vs. CV Penetration', fontsize=tsize)
    plt.xlabel('Percentage CV Penetration', fontsize=axsize,
               fontweight='bold')
    plt.ylabel('Delay [s/km]', fontsize=axsize)
    # order of magnitude of the max point
    # set x and y lims with some space around the max and min values
    plt.xticks(cvp, fontsize=ticksize, fontweight='bold')
    maxVal = max([min(l[1][0].get_ydata()[:1]) for l in lines])
    magnitude = 10**int(log10(maxVal))
    yMax = roundUp(maxVal, 0.5*magnitude)+ 10
    # double the ytick interval
    newYticks = np.arange(0, yMax+1, 0.5*magnitude, dtype=int)
    if len(newYticks) <= 8:
        newYticks = np.arange(0, yMax+1, 0.25*magnitude, dtype=int)
    elif len(newYticks) >= 18:
        newYticks = np.arange(0, yMax+1, magnitude, dtype=int)
    plt.yticks(newYticks, fontsize=ticksize, fontweight='bold')
    yMin = -0.5*newYticks[1]
    plt.ylim([yMin, yMax])
    plt.xlim([-3, 103])
    #plt.legend(labels, prop={'size': ticksize-2}, labelspacing=1,
    #    loc='upper center', bbox_to_anchor=(0.5, 1.2), ncol=4)
    savePDF(figuresPDF, fig)
    i += 1

figuresPDF.close()

'''
Crop out legend:
pdfcrop --margins '0 0 0 -600' delay.pdf legend_crop.pdf
pdfcrop --margins '0 0 0 0' legend_crop.pdf legend.pdf
pdftk legend.pdf cat 1 output legend1.pdf
mv legend1.pdf legend.pdf && rm legend_crop.pdf
'''
