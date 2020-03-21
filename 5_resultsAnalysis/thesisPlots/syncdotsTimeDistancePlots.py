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


def savePDF(pdfFile, figure):
    ''' Save figure at publication quality using desired settings
    '''
    pdfFile.savefig(figure, dpi=600, bbox_inches='tight', pad_inches=0.1)


figuresPDF = PdfPages('SYNCDOTS_TDplots.pdf')
hour2sec = 60 * 60
# start and stop times to plot trajectories over
start, stop = 7.5, 9.5
# Trajectories are for high demand and 100% CVP
resultFolder = '/hardmem/results/thesisResults/trajectories/'
transytFile = resultFolder + 'TRANSYT_routes_E117.csv'
data1 = pd.read_csv(transytFile)
data1 = data1[data1.distance > 0]
data1['time'] /= 1000.0*hour2sec
data1['distance'] /= 1000.0
data1 = data1[(data1.time > start) & (data1.time < stop)]
fig = plt.figure(figsize=(15, 9))
vehIDs = data1.vehID.unique()

for vehID in vehIDs:
    subset = data1[data1.vehID == vehID]
    plt.plot(subset.time.values, subset.distance.values, 'C0-', linewidth=0.5)

plt.title('TRANSYT Time-Distance Plot', fontsize=tsize)
plt.xlabel('Time [hours]', fontsize=axsize)
plt.ylabel('Distance [km]', fontsize=axsize)
for tick in plt.gca().xaxis.get_major_ticks():
    tick.label.set_fontsize(ticksize)
for tick in plt.gca().yaxis.get_major_ticks():
    tick.label.set_fontsize(ticksize)
savePDF(figuresPDF, fig)

cdotsFile = resultFolder + 'CDOTS_routes_E117.csv'
data2 = pd.read_csv(cdotsFile)
data2 = data2[data2.distance > 0]
data2['time'] /= 1000.0*hour2sec
data2['distance'] /= 1000.0
data2 = data2[(data2.time > start) & (data2.time < stop)]
fig = plt.figure(figsize=(15, 9))
vehIDs = data2.vehID.unique()

for vehID in vehIDs:
    subset = data2[data2.vehID == vehID]
    plt.plot(subset.time.values, subset.distance.values, 'C0-', linewidth=0.5)

plt.title('CDOTS Time-Distance Plot', fontsize=tsize)
plt.xlabel('Time [hours]', fontsize=axsize)
plt.ylabel('Distance [km]', fontsize=axsize)
for tick in plt.gca().xaxis.get_major_ticks():
    tick.label.set_fontsize(ticksize)
for tick in plt.gca().yaxis.get_major_ticks():
    tick.label.set_fontsize(ticksize)
savePDF(figuresPDF, fig)

fig = plt.figure(figsize=(15, 9))
start, stop = 7.5, 8.0
data1 = data1[(data1.time > start) & (data1.time < stop)]
data2 = data2[(data2.time > start) & (data2.time < stop)]
vehIDs = data2.vehID.unique()
for vehID in vehIDs[3::3][1:-4]:
    subset1 = data1[data1.vehID == vehID]
    subset2 = data2[data2.vehID == vehID]
    plt.plot(subset1.time.values, subset1.distance.values, 'C0--',
             linewidth=2, label='TRANSYT')
    plt.plot(subset2.time.values, subset2.distance.values, 'C1-',
             linewidth=2, label='CDOTS')

plt.title('TRANSYT vs. CDOTS Time-Distance Plot', fontsize=tsize)
plt.xlabel('Time [hours]', fontsize=axsize)
plt.ylabel('Distance [km]', fontsize=axsize)
plt.legend(['TRANSYT', 'CDOTS'], prop={'size': ticksize-9})
for tick in plt.gca().xaxis.get_major_ticks():
    tick.label.set_fontsize(ticksize)
for tick in plt.gca().yaxis.get_major_ticks():
    tick.label.set_fontsize(ticksize)
savePDF(figuresPDF, fig)

figuresPDF.close()
