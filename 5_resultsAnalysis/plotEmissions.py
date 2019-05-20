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

data = pd.read_csv('/hardmem/results/allEmissionInfo.csv', engine='c')
W = 1.0  # delay cost per second
K = 14.0  # cost per stop time to decel + time to accel for car
#data['delay'] = data['delay']/(data['routeLength']*0.001)
#data['PI'] = W*data['delay'] + K*data['stops']
models = ['sellyOak_avg', 'sellyOak_lo', 'sellyOak_hi']
modMap = {'sellyOak_avg':'Selly Oak Avg.',
          'sellyOak_lo':'Selly Oak Low',
          'sellyOak_hi':'Selly Oak High',
          'twinT': 'Twin-T','cross':'cross'}
emissionMap = {'CO2': r'$CO_2$', 'CO': 'CO', 'PMX': r'$PM_x$',
              'NOX': r'$NO_x$', 'FUEL': 'Fuel'}
controllers = ['TRANSYT', 'GPSVA', 'GPSVAslow', 'HVA']
ctrlMap = {'TRANSYT':'TRANSYT', 'GPSVA':'MATS-FT',
           'GPSVAslow':'MATS-ERR', 'HVA':'MATS-HA'}
pedStage = False
figuresPDF = PdfPages('emissions_noped.pdf')

cvp = data.cvp.unique()
for model in models:
    for emission in ['CO2', 'CO', 'PMX', 'NOX', 'FUEL']:
        fig = plt.figure(figsize=(16, 9))  # set figure size
        lines = []
        labels = []
        # iterate controllers
        
        for controller in controllers:
            plotData = data[(data.model == model) & (data.pedStage == pedStage) &
                            (data.controller == controller)]
            totalEmission = plotData.groupby('cvp')[emission].sum().values

        if controller in ['VA', 'TRANSYT']:
            totalEmission = totalEmission * np.ones_like(cvp)

        plt.plot(cvp, totalEmission, lineStyle[controller]+'-', linewidth=2, 
                 markersize=12, label=controller)
        labels.append(ctrlMap[controller])
        modName = modMap[model]
        plt.title(modName+r': Total '+emissionMap[emission]+r' emissions', fontsize=tsize)
        plt.xlabel('Percentage CV Penetration', fontsize=axsize,
                   fontweight='bold')
        plt.ylabel(emissionMap[emission]+r' emissions [mg]', fontsize=axsize)
        savePDF(figuresPDF, fig)

figuresPDF.close()

'''
Crop out legend:
pdfcrop --margins '0 0 0 -600' legend.pdf legend_crop.pdf
pdfcrop --margins '0 0 0 0' legend_crop.pdf legend.pdf
pdftk legend.pdf cat 1 output legend1.pdf
mv legend1.pdf legend.pdf && rm legend_crop.pdf
'''
