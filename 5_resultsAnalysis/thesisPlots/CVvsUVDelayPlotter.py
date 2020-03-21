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

tsize = 38
axsize = 38
ticksize = 38
nolab = '_nolegend_'


def pct(a,b):
    return 100.0*(1.0 - (a/float(b)))


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


lineStyle = {'TRANSYT': 'sk-',
             'GPSVA': 'vC3--',
             'GPSVAslow': '^C0--',
             'CDOTS': '*C1-',
             'CDOTSslow': 'oC2-'}

models = ['sellyOak_lo', 'sellyOak_avg', 'sellyOak_hi']
modMap = {'sellyOak_avg': 'Selly Oak Avg.',
          'sellyOak_lo': 'Selly Oak Low',
          'sellyOak_hi': 'Selly Oak High',
          'twinT': 'Twin-T', 'cross': 'cross'}
controllers = ['CDOTS', 'CDOTSslow']
ctrlMap = {'TRANSYT': 'TRANSYT', 'GPSVA': 'MATS',
           'GPSVAslow': 'MATS-ERR', 'HVA': 'MATS-HA',
           'CDOTS': 'CDOTS', 'CDOTSslow': 'CDOTS-ERR'}
modLim = {'sellyOak_avg': {False: [[0, 2500], 250], True: [[0, 2250], 250]},
          'sellyOak_lo': {False: [[0, 700], 50], True: [[0, 700], 50]},
          'sellyOak_hi': {False: [[0, 5000], 500], True: [[0, 7100], 1000]}}
modLimLog = {'sellyOak_avg': {False: [[1, 10**4], 0], True: [[1, 10**4], 0]},
             'sellyOak_lo': {False: [[1, 10**3], 0], True: [[1, 10**3], 0]},
             'sellyOak_hi': {False: [[1, 10**4], 0], True: [[1, 10**4], 0]}}
activationArrays = ['1111001',  # Top 5 both
                    '1101001',  # Top 4 CDOTS
                    '1111000',  # Top 4 CDOTSslow
                    '1101000']  # Top 3 both

pedStage = True if len(sys.argv) >= 2 else False
pedString = '_ped' if pedStage else ''
pdfFileName = 'CVvsUV_delaylog{}.pdf'.format(pedString)
figuresPDF = PdfPages(pdfFileName)
print('Writing: '+pdfFileName)

# only store the cols we need to save memory
selectCols = ['controller', 'model', 'run', 'cvp', 'routeLength', 'delay', 'connected']
cvps = np.arange(0, 101, 10, dtype=int)[1:-1]
i = 0
lineCycle = ['vC3-', '^C1--', '*C0-', 'oC2--']
for model in models:
    fig = plt.figure(figsize=(15, 9))  # set figure size
    lines = []
    labels = []
    # iterate controllers
    for controller in controllers:
        # subset plot data
        label = ctrlMap[controller]
        if 'CDOTS' in controller:
            file = '{}{}-{}-{}-tripinfo.csv'.format(controller,
                                                    pedString, model,
                                                    activationArrays[-1])
            # label += '-' + activationArrays[0]
        else:
            file = '{}{}-{}-tripinfo.csv'.format(controller, pedString, model)
        data = pd.read_csv('/hardmem/results/outputCSV/'+file,
                           engine='c', usecols=selectCols)
        data['delay'] = data['delay']/(data['routeLength']*0.001)
        # if no data in this set continue
        if data.empty:
            print('{} {} *NULL*'.format(model, controller))
            continue
        else:
            data = data[data.cvp.isin(cvps)]
            CVdata = data[data.connected == 1].groupby('cvp').delay 
            UVdata = data[data.connected == 0].groupby('cvp').delay
            data = 0

        CVmean = CVdata.mean().values        
        UVmean = UVdata.mean().values
        for cv_i, uv_j in zip(CVmean, UVmean):
            print(model, controller, pct(uv_j, cv_i))        

        for data in [CVdata, UVdata]:
            # get mean delay across all runs
            meanDelay = data.mean().values

            # get error limits
            err = data.apply(lambda x: np.percentile(x, [5, 95])).values
            err = np.array([[lo, hi] for lo, hi in err])
            errLims = [meanDelay-err[:, 1], err[:, 0]-meanDelay]
            lines.append(plt.errorbar(cvps, meanDelay,
                                      yerr=errLims,
                                      fmt=lineCycle[i],
                                      linewidth=2, markersize=12,
                                      label=controller,
                                      capsize=9, capthick=3, elinewidth=1))
            print(model, controller, meanDelay[-1])
            i += 1
        labels.append(label)
    modName = modMap[model]
    plt.title(modName+': Delay vs. CV Penetration', fontsize=tsize)
    plt.xlabel('Percentage CV Penetration', fontsize=axsize,
               fontweight='bold')
    plt.ylabel('Delay [s/km]', fontsize=axsize)
    # order of magnitude of the max point
    # set x and y lims with some space around the max and min values
    plt.xticks(cvps, fontsize=ticksize, fontweight='bold')
    plt.xlim([7, 93])
    yMin, yMax = modLim[model][pedStage][0]
    # plt.ylim([yMin-5, yMax+5])
    # plt.yticks(np.arange(yMin, yMax+1,
    #                      modLim[model][pedStage][1], dtype=int))
    plt.yscale('log')
    plt.ylim(modLimLog[model][pedStage][0])
    for tick in plt.gca().yaxis.get_major_ticks():
        tick.label.set_fontsize(ticksize)
    plt.grid(axis='y', which='both', alpha=0.5)
    #plt.legend(['CDOTS-CVs', 'CDOTS-UVs', 'CDOTS-ERR-CVs', 'CDOTS-ERR-UVs'], prop={'size': ticksize-12}, labelspacing=1,
    #    loc='upper center', bbox_to_anchor=(0.5, 1.2), ncol=5)
    savePDF(figuresPDF, fig)
    i = 0
figuresPDF.close()

'''
Crop out legend:
pdfcrop --margins '0 0 0 -615' CVvsUV_delaylog.pdf legend_crop.pdf
pdfcrop --margins '0 0 0 0' legend_crop.pdf legend_cdots.pdf
pdftk legend_cdots.pdf cat 1 output legend1.pdf
mv legend1.pdf legend_cdots.pdf && rm legend_crop.pdf
'''
