import pandas as pd
import numpy as np
from numpy.matlib import repmat
from matplotlib import rcParams
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from math import ceil, log10, exp
import sys
from glob import glob

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

files = ['/hardmem/outputCSV/GPSVA-simpleT-tripinfo.csv',
         '/hardmem/outputCSV/HVA-simpleT-tripinfo.csv',
         '/hardmem/outputCSV/GPSVAslow-simpleT-tripinfo.csv',
         '/hardmem/outputCSV/CDOTS-simpleT-1101000-tripinfo.csv',
         '/hardmem/outputCSV/CDOTSslow-simpleT-1101000-tripinfo.csv']
MOVAdelay = 20.3
cvps = np.arange(0,101, 10, dtype=int)
ctrlMap = {'TRANSYT': 'TRANSYT', 'GPSVA': 'MATS-FT',
           'GPSVAslow': 'MATS-ERR', 'HVA': 'MATS-HA',
           'CDOTS': 'CDOTS', 'CDOTSslow': 'CDOTS-ERR'}
lineStyle = {'MOVA': 'sk-',
             'GPSVA': 'vC0-',
             'GPSVAslow': '^C2-',
             'HVA': 'dC9-',
             'CDOTS': '*C3-',
             'CDOTSslow': 'oC1-'}
# lineStyle = {'MOVA': 'sk-',
#              'GPSVA': 'vC3-',
#              'GPSVAslow': '^C1--',
#              'HVA': 'XC2-'}

fig = plt.figure(figsize=(16, 9))
MOVAline = MOVAdelay*np.ones_like(cvps)
plt.plot(cvps, MOVAline, lineStyle['MOVA'],
         linewidth=2, markersize=12, label='MOVA')

for file in files:
    print(file)
    controller = file.split('/')[-1].split('-')[0]
    df = pd.read_csv(file)
    delays = df.groupby('cvp').delay.mean().values
    delays[delays > delays[0]] = delays[0]
    plt.plot(cvps, delays, lineStyle[controller],
             linewidth=2, markersize=12, label=ctrlMap[controller])

plt.title('Delay vs. CV Penetration', fontsize=tsize)
plt.xlabel('Percentage CV Penetration', fontsize=axsize,
           fontweight='bold')
plt.ylabel('Delay [s]', fontsize=axsize)
# order of magnitude of the max point
# set x and y lims with some space around the max and min values
plt.xlim([-3, 103])
plt.ylim([14, 28])
plt.xticks(cvps, fontsize=ticksize, fontweight='bold')
plt.yticks(np.arange(14, 28.1, 1, dtype=int), fontsize=ticksize, fontweight='bold')
for tick in plt.gca().yaxis.get_major_ticks():
    tick.label.set_fontsize(ticksize)
plt.grid(axis='y', which='both', alpha=0.5)
plt.legend(fontsize=24)
plt.savefig('movaDelay.pdf', dpi=600, bbox_inches='tight', pad_inches=0.1)