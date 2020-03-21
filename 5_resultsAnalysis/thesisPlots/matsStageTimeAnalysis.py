# -*- coding: utf-8 -*-
"""
Created on Mon Oct 14 07:46:59 2019

@author: craig
"""
import numpy as np
import pandas as pd
from matplotlib import rcParams
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from glob import glob
import re

# Use T1 fonts for plots not bitmap
rcParams['ps.useafm'] = True
rcParams['pdf.use14corefonts'] = True
rcParams['text.usetex'] = True
plt.rcParams["font.family"] = "Times New Roman"
# We're using tex fonts so we need to bolden all text in the preambles
# not with fontweight='bold'
rcParams['text.latex.preamble'] = \
    [r'\renewcommand{\seriesdefault}{\bfdefault}']

tsize = 20
axsize = 22
ticksize = 20
nolab = '_nolegend_'


def savePDF(pdfFile, figure):
    ''' Save figure at publication quality using desired settings
    '''
    pdfFile.savefig(figure, dpi=600,
                    # bbox_extra_artists=(lgnd,),
                    bbox_inches='tight', pad_inches=0.1)


def pathParse(path):
    regex = '/hardmem/results/(.+?)/(.+?)/stageinfo_R(.+?)_CVP(.+?).csv'
    match = re.match(regex, path)
    controller, model, run, cvp = match.groups()
    return controller, model, int(run), int(cvp)

stagefiles = glob('/hardmem/results/**/**/stageinfo*.csv')
data = []
for fname in stagefiles:
    controller, model, run, cvp = pathParse(fname)
    if '_ped' in controller or 'TRANSYT' in controller:
        df = pd.read_csv(fname)        
        df['controller'] = controller
        df['model'] = model
        df['run'] = run
        df['cvp'] = cvp
        df['stop'] = df.simTime.values # when the occurance ended
        df['start'] = df.simTime.values - df.stageDuration.values # when the occurance started
        df['interval'] = 0.0 # preallocate interval
        for junc in df.junction.unique():
            subset1 = df[df.junction == junc]
            for stage in subset1.stageID.unique():
                subset2 = subset1[subset1.stageID == stage]
                # interval between when the last occurance stopped and the current occruance 
                # offset to create time shift
                interval = subset2.start.values[1:] - subset2.stop.values[:-1]
                interval = np.array([0.0]+list(interval))
                df.loc[(df.junction == junc)&(df.stageID == stage), 'interval'] = interval
        data.append(df)

'''        
pd.set_option('display.float_format', '{:5,.2f}'.format)
pd.set_option('display.max_rows', None)

grouping = data.groupby(['junction', 'stageID'])
print(grouping.deltas.mean())
print(grouping.deltas.max())
print(grouping.deltas.apply(lambda x: np.percentile(x, (5,95))))
'''
data = pd.concat(data, ignore_index=True)
controllers = ['GPSVA_ped']
models = ['sellyOak_lo', 'sellyOak_avg', 'sellyOak_hi']
juncs = ['junc3', 'junc5', 'junc9']
cvps = [100]

lineStyle = {'TRANSYT': 'sk-',
             'GPSVA': 'vC3-',
             'GPSVAslow': '^C1--',             
             'HVA': 'XC2-'}

modMap = {'sellyOak_avg':'Selly Oak Avg.',
          'sellyOak_lo':'Selly Oak Low',
          'sellyOak_hi':'Selly Oak High',
          'twinT': 'Twin-T','cross':'cross'}
modLim = {'sellyOak_lo':{False:[[0, 4.5], 0.5], True:[[0, 4.5], 0.5]},
          'sellyOak_avg':{False:[[0, 5], 0.5], True:[[0, 9], 1]},
          'sellyOak_hi':{False:[[0, 7.5], 0.5], True:[[0, 12], 1]}}
ctrlMap = {'TRANSYT':'TRANSYT', 'GPSVA':'MATS',
           'GPSVAslow':'MATS-ERR', 'HVA':'MATS-HA',
           'CDOTS':'CDOTS', 'CDOTSslow':'CDOTS-ERR'}

pdfFileName = 'MATS_stageTimes.pdf'
figuresPDF = PdfPages(pdfFileName)
print('Writing: '+pdfFileName)

bins = np.arange(40,161,5,dtype=int)
labels = ['Low Flow', 'Avg. Flow', 'High Flow']

for junc in juncs:
    #stages = data[data.junction==junc].stageID.unique()
    #for stage in stages:
    for cvp in [0]:
        for controller in controllers:
            fig = plt.figure(figsize=(7, 4))
            means = []
            PI95 = []
            for i, model in enumerate(models):
                df = data[(data.junction == junc) &
                          (data.cvp == cvp) &
                          (data.controller == controller) &
                          (data.model == model) &
                          #(data.stageID == stage) &
                          (data.interval > 1)]
                means.append(df.interval.mean())
                PI95.append(np.round(np.percentile(df.interval, [2.5, 97.5])))
                plt.hist(df.interval, histtype='step', bins=bins, label=labels[i], linewidth=1.5)
            ctrlName = ctrlMap[controller.split('_')[0]]
            titleStr = 'J{}: TRANSYT stage interval histogram'.format(junc[-1], ctrlName)
            plt.title(titleStr,fontsize=tsize, fontweight='bold')
            plt.xlabel('Stage interval [s]', fontsize=axsize, fontweight='bold')
            plt.ylabel('Frequency', fontsize=axsize, fontweight='bold')
            plt.gca().xaxis.set_ticks(np.arange(40,161,10,dtype=int))
            plt.gca().xaxis.set_ticks(np.arange(45,156,5,dtype=int), minor=True)
            for tick in plt.gca().xaxis.get_major_ticks():
                tick.label.set_fontsize(ticksize)
            for tick in plt.gca().yaxis.get_major_ticks():
                tick.label.set_fontsize(ticksize)
            if '3' in junc or  '5' in junc:
                lloc = 'upper left'
            else:
                lloc = 'best'
            plt.legend(prop={'size': 14}, loc=lloc)
            '''
            text = ('Low mean: {:.2f}\n'+
                    'Avg. Mean: = {:.2f}\n'+
                    'High Mean = {:.2f}\n').format(*means)
            PI95 = ["[{}, {}]".format(*x) for x in PI95]
            text += ('Low 95\% PI: {}\n'+
                     'Avg. 95\% PI: = {}\n'+
                     'High 95\% PI = {}').format(*PI95)
            plt.text(120, 0.25*max(plt.yticks()[0]), text, fontsize=14)
            '''            
            savePDF(figuresPDF, fig)

for junc in juncs:
    #stages = data[data.junction==junc].stageID.unique()
    #for stage in stages:
    for cvp in cvps:
        for controller in controllers:
            fig = plt.figure(figsize=(7, 4))
            means = []
            PI95 = []
            for i, model in enumerate(models):
                df = data[(data.junction == junc) &
                          (data.cvp == cvp) &
                          (data.controller == controller) &
                          (data.model == model) &
                          #(data.stageID == stage) &
                          (data.interval > 1)]
                means.append(df.interval.mean())
                PI95.append(np.round(np.percentile(df.interval, [2.5, 97.5])))
                plt.hist(df.interval, histtype='step', bins=bins, label=labels[i], linewidth=1.5)
            ctrlName = ctrlMap[controller.split('_')[0]]
            titleStr = 'J{}: {} stage interval histogram'.format(junc[-1], ctrlName)
            plt.title(titleStr,fontsize=tsize, fontweight='bold')
            plt.xlabel('Stage interval [s]', fontsize=axsize, fontweight='bold')
            plt.ylabel('Frequency', fontsize=axsize, fontweight='bold')
            plt.gca().xaxis.set_ticks(np.arange(40,161,10,dtype=int))
            plt.gca().xaxis.set_ticks(np.arange(45,156,5,dtype=int), minor=True)
            for tick in plt.gca().xaxis.get_major_ticks():
                tick.label.set_fontsize(ticksize)
            for tick in plt.gca().yaxis.get_major_ticks():
                tick.label.set_fontsize(ticksize)
            plt.legend(prop={'size': 14})
            '''
            text = ('Low mean: {:.2f}\n'+
                    'Avg. Mean: = {:.2f}\n'+
                    'High Mean = {:.2f}\n').format(*means)
            PI95 = ["[{}, {}]".format(*x) for x in PI95]
            text += ('Low 95\% PI: {}\n'+
                     'Avg. 95\% PI: = {}\n'+
                     'High 95\% PI = {}').format(*PI95)
            plt.text(120, 0.25*max(plt.yticks()[0]), text, fontsize=14)
            '''            
            savePDF(figuresPDF, fig)
figuresPDF.close()
                        
            

