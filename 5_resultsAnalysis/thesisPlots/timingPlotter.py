import pandas as pd
import numpy as np
from numpy.matlib import repmat
from matplotlib import rcParams
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from math import ceil, log10, exp
import sys
from glob import glob
from sklearn import linear_model

# Use T1 fonts for plots not bitmap
rcParams['ps.useafm'] = True
rcParams['pdf.use14corefonts'] = True
rcParams['text.usetex'] = True
plt.rcParams["font.family"] = "Times New Roman"
# We're using tex fonts so we need to bolden all text in the preambles
# not with fontweight='bold'
rcParams['text.latex.preamble'] = \
    [r'\renewcommand{\seriesdefault}{\bfdefault}']


def savePDF(pdfFile, figure):
    ''' Save figure at publication quality using desired settings
    '''
    pdfFile.savefig(figure, dpi=600, bbox_inches='tight', pad_inches=0.1)


def slope(xdata, ydata):
    return (ydata[-1] - ydata[0])/(xdata[-1] - xdata[0])

def x_intercept(xdata, ydata, target_y=0.0, c=0.0):
    return (target_y - c)/slope(xdata, ydata)

def linModReverse(xdata, ydata, target_y=0.0):
    # linear model to predict the x value that gives target_y from the data 
    lm = linear_model.LinearRegression()
    model = lm.fit(ydata.reshape(-1,1), xdata)
    # Print R^2 values
    # print(lm.score(ydata.reshape(-1,1), xdata))
    return model.predict(target_y)

def x_intercept2(xdata, ydata, target_y=0.0, c=0.0):
    # See if data exists either side of line and work out the intercep between
    # those two points. If not use linear regression.
    try:
        for i, (x, y) in enumerate(zip(xdata, ydata)):
            if y > target_y:
                x1, y1 = xdata[i-1], ydata[i-1] 
                x2, y2 = xdata[i], ydata[i]
                m = (y2 - y1)/(x2 - x1)
                break
        return (target_y - c)/m
    except:
        #return x_intercept(xdata, ydata, target_y)
        return linModReverse(xdata, ydata, target_y)

tsize = 38
axsize = 38
ticksize = 30
nolab = '_nolegend_'

folders = ['/hardmem/results/TRANSYT_ped/sellyOak_hi/',
           '/hardmem/results/CDOTS_ped/sellyOak_hi/1101000/',
           '/hardmem/results/CDOTSslow_ped/sellyOak_hi/1101000/']

xvals = np.arange(12,1201,12)
figuresPDF = PdfPages('timingPlot.pdf')

for folder in folders:
    fig = plt.figure(figsize=(16, 9))
    thresholdLine = 0.1*np.ones(2)
    plt.plot([12, 1200], thresholdLine, 'k',
             linewidth=5, label='Tcap')

    data = []
    for i, file in enumerate(glob(folder+'timinginfo*.csv')):
        df = np.loadtxt(file, delimiter=',')
        data.append(df)
    data = np.vstack(data)
    

    maxData = np.max(data, axis=0)
    meanData = np.mean(data, axis=0)
    minData = np.min(data, axis=0)
    piData = np.percentile(data, [2.5, 97.5], axis=0)
    plt.plot(xvals, maxData, '^C7-', linewidth=1, markersize=8, label='Max.')
    plt.plot(xvals, minData, 'vC7-', linewidth=1, markersize=8, label='Min.')
    errLims = [meanData - piData[1,:], piData[0,:] - meanData]
    #plt.plot(xvals, meanData, 'oC0-', linewidth=1, markersize=8, label='Mean')
    plt.errorbar(xvals, meanData,
                 yerr=errLims,
                 fmt='oC0-',
                 linewidth=1, markersize=8,
                 label='Mean',
                 capsize=3, capthick=2, elinewidth=1)

    print(folder)
    print('Min Intercept: '+str(np.floor(x_intercept2(xvals, maxData, 0.1))))
    print('97.5th Percentile Intercept: '+str(np.floor(x_intercept2(xvals, piData[1,:], 0.1))))
    print('Mean Intercept: '+str(np.floor(x_intercept2(xvals, meanData, 0.1))))
    print('2.5th Percentile Intercept: '+str(np.floor(x_intercept2(xvals, piData[0,:], 0.1))))
    print('Max Intercept: '+str(np.floor(x_intercept2(xvals, minData, 0.1))))
    print('')

    plt.title('Execution Time vs. No. Controllers', fontsize=tsize)
    plt.xlabel('Number of Controller Processes', fontsize=axsize)
    plt.ylabel('Time [s]', fontsize=axsize)
    # order of magnitude of the max point
    # set x and y lims with some space around the max and min values
    plt.xlim([0, 1212])
    plt.xticks(np.arange(0, 1201, 100, dtype=int), fontsize=ticksize, fontweight='bold')
    if 'TRANSYT' not in folder:
        plt.yticks(np.arange(0, max(maxData)+0.1, 0.1), fontsize=ticksize, fontweight='bold')
    else:
        plt.ylim([-0.0025, .103])
        plt.yticks(np.arange(0, 0.11 , 0.01), fontsize=ticksize, fontweight='bold')
    plt.grid(axis='y', which='both', alpha=0.5)
    plt.legend(fontsize=24)
    savePDF(figuresPDF, fig)

figuresPDF.close()
