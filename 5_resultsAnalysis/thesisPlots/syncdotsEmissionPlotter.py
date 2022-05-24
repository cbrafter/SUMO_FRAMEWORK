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


def roundUp(x, num):
    return int(ceil(x / float(num))) * int(num)


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


lineStyle = {'TRANSYT': 'vk',
             'GPSVAslow': '^C0',
             'CDOTS': 'vC1',
             'CDOTSslow': 'vC2',
             'SynCDOTS': '^C5',
             'SynCDOTSslow': '^C6',
             'GPSVA': '*C3',
             'HVA': 'oC4'}

activationArrays = ['1111001',  # Top 5 both
                    '1101001',  # Top 4 CDOTS
                    '1111000',  # Top 4 CDOTSslow
                    '1101000']  # Top 3 both

models = ['sellyOak_lo', 'sellyOak_avg', 'sellyOak_hi']
modMap = {'sellyOak_avg': 'Selly Oak Avg.',
          'sellyOak_lo': 'Selly Oak Low',
          'sellyOak_hi': 'Selly Oak High',
          'twinT': 'Twin-T', 'cross': 'cross'}
emissions = ['FUEL']

emissionMap = {'CO2': r'$CO_2$', 'CO': 'CO', 'PMX': r'$PM_x$',
               'NOX': r'$NO_x$', 'FUEL': 'Fuel'}
unitMap = {'CO2': '[tonnes]', 'CO': '[tonnes]', 'PMX': '[kg]',
           'NOX': '[kg]', 'FUEL': '[kl]'}
unitScale = {'CO2': 1e-9, 'CO': 1e-9, 'PMX': 1e-6,
             'NOX': 1e-6, 'FUEL': 1e-6}
controllers = ['TRANSYT', 'GPSVA', 'GPSVAslow', 'CDOTS', 'CDOTSslow']
ctrlMap = {'TRANSYT': 'TRANSYT', 'GPSVA': 'MATS',
           'GPSVAslow': 'MATS-ERR', 'HVA': 'MATS-HA',
           'CDOTS': r'$\alpha=0$', 'CDOTSslow': 'CDOTS-ERR',
           'SynCDOTS': 'CDOTS-', 'SynCDOTSslow': 'SynCDOTS-ERR'}
pedStage = True if len(sys.argv) >= 2 else False
pedString = '_ped' if pedStage else ''
pdfFileName = 'SYNCDOTS_emissions{}.pdf'.format(pedString)
figuresPDF = PdfPages(pdfFileName)
print('Writing: ' + pdfFileName)

i = 0
pointStyles = ['*', 'o', '^', 'v', 'x']
syncdotsCfg = []
for ctrl in ['SynCDOTS']:
    for syncStrength in ['25', '50', '75', '100']:
        for syncMode in ['PS']:
            syncdotsCfg.append(ctrl + '_' + syncStrength + '_' + syncMode)

cvp = np.arange(0, 101, 10, dtype=int)
for model in models:
    data = {}
    for emission in emissions:
        fig = plt.figure(figsize=(14, 9))  # set figure size
        lines = []
        labels = []

        # iterate controllers
        for ctrl in ['CDOTS'] + syncdotsCfg:
            controller = ctrl.split('_')[0]
            label = ctrlMap[controller]
            if 'SynCDOTS' in controller:
                controller, syncStrength, syncMode = ctrl.split('_')
                file = '{}{}-{}-{}_{}_{}-emissions.csv'.format(controller,
                                                               pedString,
                                                               model,
                                                               activationArrays[3],
                                                               syncStrength,
                                                               syncMode)
                label = r'$\alpha={}$'.format(float(syncStrength) / 100.0)
                # label += '-' + activationArrays[0]
            elif 'CDOTS' in controller:
                file = '{}{}-{}-{}-emissions.csv'.format(
                    controller, pedString, model, activationArrays[3])
                # label += '-' + activationArrays[0]
            else:
                file = '{}{}-{}-emissions.csv'.format(controller, pedString, model)
            if file not in data.keys():
                data[file] = pd.read_csv(
                    '/hardmem/results/outputCSV/' + file, engine='c')
            # plotData = data[(data.model == model) &
            #                 (data.pedStage == pedStage) &
            #                 (data.controller == controller)]
            totalEmission = (data[file].groupby(['cvp', 'run'])[emission]
                                       .sum()
                                       .reset_index()
                                       .groupby('cvp')[emission]
                                       .mean().values)

            if controller in ['VA', 'TRANSYT']:
                totalEmission = totalEmission[0] * np.ones_like(cvp)
            scaledEmission = (unitScale[emission] * totalEmission)[1:]
            plt.plot(cvp[1:], scaledEmission,
                     pointStyles[i % 5] + '-C' + str(i % 5), linewidth=2,
                     markersize=12, label=controller)
            labels.append(ctrlMap[controller])
            print(model, syncStrength, scaledEmission)
            i += 1
        modName = modMap[model]
        plt.title(modName + r': Total ' +
                  emissionMap[emission] + r' emissions', fontsize=tsize)
        plt.xticks(cvp, fontsize=ticksize, fontweight='bold')
        yticks = plt.yticks()[0]
        plt.yticks(yticks, fontsize=ticksize, fontweight='bold')
        plt.xlabel('Percentage CV Penetration', fontsize=axsize,
                   fontweight='bold')
        plt.ylabel(emissionMap[emission] + r' emissions ' +
                   unitMap[emission], fontsize=axsize)
        savePDF(figuresPDF, fig)
        print('Plotted: ' + model + ' ' + emission)

figuresPDF.close()