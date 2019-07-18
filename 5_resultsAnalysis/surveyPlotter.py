# -*- coding: utf-8 -*-
"""
Created on Fri Jul  5 09:41:12 2019

@author: craig
"""

import numpy as np
import pandas as pd
from matplotlib import rcParams
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.ticker as tck
from mpl_toolkits.axes_grid1 import make_axes_locatable


# Use T1 fonts for plots not bitmap
rcParams['ps.useafm'] = True
rcParams['pdf.use14corefonts'] = True
rcParams['text.usetex'] = True
plt.rcParams["font.family"] = "Times New Roman"
plt.rcParams.update({'figure.max_open_warning': 0})
# We're using tex fonts so we need to bolden all text in the preambles
# not with fontweight='bold'
rcParams['text.latex.preamble'] = \
    [r'\renewcommand{\seriesdefault}{\bfdefault}']

tsize = 20
axsize = 18
ticksize = 16
nolab = '_nolegend_'


def savePDF(pdfFile, figure):
    ''' Save figure at publication quality using desired settings
    '''
    pdfFile.savefig(figure, dpi=600,
                    # bbox_extra_artists=(lgnd,),
                    bbox_inches='tight', pad_inches=0.1)

data = pd.read_csv('./SurveyData_clean.csv')

def rangeMap(x, inRange, outRange):
    """"Maps a range e.g. 1-5 scale to -1 - 1 for sentiment analysis
    using an affine transformation
    https://math.stackexchange.com/questions/377169/calculating-a-value-inside-one-range-to-a-value-of-another-range
    e.g. rangeMap(3, [1, 5], [-1, 1]) >> 0"""
    inMin, inMax = [float(val) for val in sorted(inRange)]
    outMin, outMax = [float(val) for val in sorted(outRange)]
    slope = (outMax - outMin) / (inMax - inMin)
    return (x - inMin) * slope + outMin

def likertMap(x):
    return rangeMap(x, [1, 5], [-1, 1])
    
def likertMap10(x):
    return rangeMap(x, [1, 10], [-1, 1])
        
def enumSeries(pdSeries):
    """Enumerates text field series"""
    assert pdSeries.dtype == 'O', 'ERROR: Series must be string type objects'
    cleanSeries = pdSeries.fillna('NA')
    uniqueVals = sorted(cleanSeries.unique())
    labelMap = {k:v for v,k in enumerate(uniqueVals)}
    return cleanSeries.apply(lambda x: labelMap[x]), labelMap
    

pdfFileName = 'surveyPlots.pdf'
figuresPDF = PdfPages(pdfFileName)

###########################################################################
# SECTION 1: BACKGROUND
###########################################################################
# Age
objects = sorted(data.age.unique())
x_pos = np.arange(len(objects))
scale = 100.0/float(data.age.count())
values = [data.age[data.age==x].count()*scale for x in objects]

fig = plt.figure()
plt.bar(x_pos, values, align='center', width=0.5)
plt.xticks(x_pos, objects, fontsize=ticksize, fontweight='bold')
plt.ylim([0,100])
plt.yticks(np.arange(0,101,10), fontsize=ticksize, fontweight='bold')
plt.ylabel('Percentage', fontsize=axsize)
plt.title('Age Demographic', fontsize=tsize)
plt.grid(axis='y', linestyle='--', linewidth=1, alpha=0.5)
savePDF(figuresPDF, fig)

# Gender
total = data.gender.count()
male = 100*data.gender[data.gender=='Male'].count()/float(total)
female = 100*data.gender[data.gender=='Female'].count()/float(total)
LGBTQ = 100*data.gender[data.gender=='LGBTQ'].count()/float(total)

objects = ('Male', 'Female', 'LGBTQ+')
x_pos = np.arange(len(objects))
values = [male, female, LGBTQ]

fig = plt.figure()
plt.bar(x_pos, values, align='center', width=0.5)
plt.xticks(x_pos, objects, fontsize=ticksize, fontweight='bold')
plt.ylim([0,100])
plt.yticks(np.arange(0,101,10), fontsize=ticksize, fontweight='bold')
plt.ylabel('Percentage', fontsize=axsize)
plt.title('Gender Demographic', fontsize=tsize)
plt.grid(axis='y', linestyle='--', linewidth=1, alpha=0.5)
savePDF(figuresPDF, fig)

# Education
objects = ['HIGHSCHOOL', 'DIPLOMA', 'BACHELORS', 'MASTERS', 'DOCTORATE', 'OTHER']
labels = ['Secondary', 'Diploma', 'Bachelor\'s', 'Master\'s', 'Doctorate', 'Other']
x_pos = np.arange(len(objects))
scale = 100.0/float(data.education.count())
values = [data.education[data.education==x].count()*scale for x in objects]

fig = plt.figure()
plt.bar(x_pos, values, align='center', width=0.5)
plt.xticks(x_pos, labels, fontsize=ticksize, fontweight='bold', rotation=90)
plt.ylim([0,50])
plt.yticks(np.arange(0,51,5), fontsize=ticksize, fontweight='bold')
plt.ylabel('Percentage', fontsize=axsize)
plt.title('Education Demographic', fontsize=tsize)
plt.grid(axis='y', linestyle='--', linewidth=1, alpha=0.5)
savePDF(figuresPDF, fig)

# Social Media Usage
data.socialMediaUsage.fillna('NA', inplace=True)
objects = ['DAILY', 'WEEKLY_MULTI', 'WEEKLY_ONCE', 'MONTHLY', 'RARELY', 'NA']
labels = ['Daily', 'Weekly', 'Once Weekly', 'Monthly', 'Rarely', 'NA']
x_pos = np.arange(len(objects))
scale = 100.0/float(data.socialMediaUsage.count())
values = [data.socialMediaUsage[data.socialMediaUsage==x].count()*scale for x in objects]

fig = plt.figure()
plt.bar(x_pos, values, align='center', width=0.5)
plt.xticks(x_pos, labels, fontsize=ticksize, fontweight='bold', rotation=90)
plt.ylim([0,70])
plt.yticks(np.arange(0,71,5), fontsize=ticksize, fontweight='bold')
plt.ylabel('Percentage', fontsize=axsize)
plt.title('Social Media Usage', fontsize=tsize)
plt.grid(axis='y', linestyle='--', linewidth=1, alpha=0.5)
savePDF(figuresPDF, fig)

# Social Media Acceptance 1-10
objects = []
scale = 100.0/float(data.socialMediaAcceptance.count())
for i in range(1, 11): 
    objects.append(data[data.socialMediaAcceptance==i].socialMediaAcceptance.count())
x_pos = np.arange(1, len(objects)+1)
fig = plt.figure()
plt.bar(x_pos, objects, align='center', width=0.5)
plt.xticks(x_pos, fontsize=ticksize, fontweight='bold')
plt.ylim([0,20])
plt.yticks(np.arange(0,21,2), fontsize=ticksize, fontweight='bold')
plt.xlabel('Likert Scale', fontsize=axsize)
plt.ylabel('Percentage', fontsize=axsize)
plt.title('Social Media Data Sharing Acceptance', fontsize=tsize-4)
plt.grid(axis='y', linestyle='--', linewidth=1, alpha=0.5)
savePDF(figuresPDF, fig)
print('Social Media Mean Score', data.socialMediaAcceptance.mean())
print('Social Media Median Score', data.socialMediaAcceptance.median())
print('Social Media Std Score', data.socialMediaAcceptance.std())
print('Social Media Sentiment Score', 100*data.socialMediaAcceptance.apply(likertMap10).mean())

# Social Media Acceptance 1-5: down sample the above likert
objects = []
data['socialMediaAcceptanceDS'] = ((data.socialMediaAcceptance/2.0)+0.1).apply(np.round).apply(int)
scale = 100.0/float(data.socialMediaAcceptanceDS.count())
for i in range(1, 6): 
    objects.append(data[data.socialMediaAcceptanceDS==i].socialMediaAcceptanceDS.count())
x_pos = np.arange(1, len(objects)+1)
fig = plt.figure()
plt.bar(x_pos, objects, align='center', width=0.5)
plt.xticks(x_pos, fontsize=ticksize, fontweight='bold')
plt.ylim([0,50])
plt.yticks(np.arange(0,51,5), fontsize=ticksize, fontweight='bold')
plt.xlabel('Likert Scale', fontsize=axsize)
plt.ylabel('Percentage', fontsize=axsize)
plt.title('Social Media Data Sharing Acceptance', fontsize=tsize-4)
plt.grid(axis='y', linestyle='--', linewidth=1, alpha=0.5)
savePDF(figuresPDF, fig)


###########################################################################
# SECTION 2: TRANSPORT PREFERENCES
###########################################################################
# Drivers License
total = data.hasLicence.count()
yes = 100*data.hasLicence[data.hasLicence=='YES'].count()/float(total)
no = 100*data.hasLicence[data.hasLicence=='NO'].count()/float(total)
NA = 100*data.hasLicence[data.hasLicence=='NA'].count()/float(total)

objects = ('YES', 'NO', 'NA')
x_pos = np.arange(len(objects))
values = [yes, no, NA]

fig = plt.figure()
plt.bar(x_pos, values, align='center', width=0.5)
plt.xticks(x_pos, ['Yes', 'No', 'NA'], fontsize=ticksize, fontweight='bold')
plt.ylim([0,100])
plt.yticks(np.arange(0,101,10), fontsize=ticksize, fontweight='bold')
plt.ylabel('Percentage', fontsize=axsize)
plt.title('Full Driving Licence', fontsize=tsize)
plt.grid(axis='y', linestyle='--', linewidth=1, alpha=0.5)
savePDF(figuresPDF, fig)

# Car Access
total = data.hasLicence.count()
yes = 100*data.hasCarAccess[data.hasCarAccess=='YES'].count()/float(total)
no = 100*data.hasCarAccess[data.hasCarAccess=='NO'].count()/float(total)
NA = 100*data.hasCarAccess[data.hasCarAccess=='NA'].count()/float(total)

objects = ('YES', 'NO', 'NA')
x_pos = np.arange(len(objects))
values = [yes, no, NA]

fig = plt.figure()
plt.bar(x_pos, values, align='center', width=0.5)
plt.xticks(x_pos, ['Yes', 'No', 'NA'], fontsize=ticksize, fontweight='bold')
plt.ylim([0,100])
plt.yticks(np.arange(0,101,10), fontsize=ticksize, fontweight='bold')
plt.ylabel('Percentage', fontsize=axsize)
plt.title('Car Access', fontsize=tsize)
plt.grid(axis='y', linestyle='--', linewidth=1, alpha=0.5)
savePDF(figuresPDF, fig)

# Public Transport/Ride share
data.rideShareUsage.fillna('NA', inplace=True)
objects = ['WEEKLY_MULTI', 'WEEKLY_ONCE', 'MONTHLY', 'RARELY', 'NA']
labels = ['Daily', 'Weekly', 'Monthly', 'Rarely', 'NA']
x_pos = np.arange(len(objects))
scale = 100.0/float(data.rideShareUsage.count())
values = [data.rideShareUsage[data.rideShareUsage==x].count()*scale for x in objects]

fig = plt.figure()
plt.bar(x_pos, values, align='center', width=0.5)
plt.xticks(x_pos, labels, fontsize=ticksize, fontweight='bold', rotation=90)
plt.ylim([0,50])
plt.yticks(np.arange(0,51,5), fontsize=ticksize, fontweight='bold')
plt.ylabel('Percentage', fontsize=axsize)
plt.title('Public Transport/Ride-share Usage', fontsize=tsize-2)
plt.grid(axis='y', linestyle='--', linewidth=1, alpha=0.5)
savePDF(figuresPDF, fig)

# Foot/Bike frequency
data.pedCycleFreq.fillna('NA', inplace=True)
objects = ['WEEKLY_MULTI', 'WEEKLY_ONCE', 'MONTHLY', 'RARELY', 'NA']
labels = ['Daily', 'Weekly', 'Monthly', 'Rarely', 'NA']
x_pos = np.arange(len(objects))
scale = 100.0/float(data.pedCycleFreq.count())
values = [data.pedCycleFreq[data.pedCycleFreq==x].count()*scale for x in objects]

fig = plt.figure()
plt.bar(x_pos, values, align='center', width=0.5)
plt.xticks(x_pos, labels, fontsize=ticksize, fontweight='bold', rotation=90)
plt.ylim([0,60])
plt.yticks(np.arange(0,61,5), fontsize=ticksize, fontweight='bold')
plt.ylabel('Percentage', fontsize=axsize)
plt.title('Pedestrian/Cycle Frequency', fontsize=tsize)
plt.grid(axis='y', linestyle='--', linewidth=1, alpha=0.5)
savePDF(figuresPDF, fig)

# Vehicle Usage Ranking
fig = plt.figure()
groups = ['rank_car', 'rank_ev', 'rank_bus', 'rank_motorbike',
          'rank_lgv', 'rank_hgv', 'rank_none']
n_groups = len(groups)
FIRST = []
SECOND = []
THIRD = []

for group in groups:
    scale = 100.0/float(data[group].count())
    FIRST.append(scale*data[group][data[group]==1].count())
    SECOND.append(scale*data[group][data[group]==2].count())
    THIRD.append(scale*data[group][data[group]==3].count())

# create plot
index = np.arange(n_groups)
bar_width = 0.5

rects1 = plt.bar(index, FIRST, bar_width,
color='C0', label='1st')

rects2 = plt.bar(index, SECOND, bar_width,
color='C1', label='2nd', bottom=FIRST)

rects3 = plt.bar(index, THIRD, bar_width,
color='C2', label='3rd', bottom=np.add(FIRST, SECOND))

plt.ylim([0,80])
plt.yticks(np.arange(0,81,10), fontsize=ticksize-1, fontweight='bold')
ax = plt.gca()
ax.yaxis.set_minor_locator(tck.MultipleLocator(5))
plt.grid(axis='y', linestyle='--', linewidth=1, alpha=0.5)
plt.grid(axis='y', linestyle=':', linewidth=1, alpha=0.5, which='minor')
plt.ylabel('Percentage', fontsize=axsize-2)
plt.title('Most Frequently Used Transport Mode', fontsize=tsize-4)
plt.xticks(index, ('Car', 'EV', 'Bus', 'M/cycle', 'LGV', 'HGV', 'None'), fontsize=ticksize, fontweight='bold', rotation=90)
plt.legend(loc='upper center', bbox_to_anchor=(0.5, 1.26), ncol=3, fontsize=axsize-4)
savePDF(figuresPDF, fig)

# Traffic Light Gripe
data.tlGripe.fillna('None', inplace=True)
objects = ['STARTSTOP', 'WAITING', 'SUDDENRED', 'None']
labels = ['Stopping', 'Waiting', 'Sudden Red', 'None']
x_pos = np.arange(len(objects))
scale = 100.0/float(data.tlGripe.count())
values = [data.tlGripe[data.tlGripe==x].count()*scale for x in objects]

fig = plt.figure()
plt.bar(x_pos, values, align='center', width=0.5)
plt.xticks(x_pos, labels, fontsize=ticksize, fontweight='bold', rotation=90)
plt.ylim([0,50])
plt.yticks(np.arange(0,51,5), fontsize=ticksize, fontweight='bold')
plt.ylabel('Percentage', fontsize=axsize)
plt.title('Traffic Light Frustration Sources', fontsize=tsize-2)
plt.grid(axis='y', linestyle='--', linewidth=1, alpha=0.5)

# Map Usage
data.pedCycleFreq.fillna('NA', inplace=True)
objects = ['WEEKLY_MULTI', 'WEEKLY_ONCE', 'MONTHLY', 'RARELY', 'NA']
labels = ['Daily', 'Weekly', 'Monthly', 'Rarely', 'NA']
x_pos = np.arange(len(objects))
scale = 100.0/float(data.pedCycleFreq.count())
values = [data.pedCycleFreq[data.pedCycleFreq==x].count()*scale for x in objects]

fig = plt.figure()
plt.bar(x_pos, values, align='center', width=0.5)
plt.xticks(x_pos, labels, fontsize=ticksize, fontweight='bold', rotation=90)
plt.ylim([0,60])
plt.yticks(np.arange(0,61,5), fontsize=ticksize, fontweight='bold')
plt.ylabel('Percentage', fontsize=axsize)
plt.title('Navigator Usage', fontsize=tsize)
plt.grid(axis='y', linestyle='--', linewidth=1, alpha=0.5)
savePDF(figuresPDF, fig)

# Live traffic usage
data.mapHelp.fillna('NA', inplace=True)
total = data.mapHelp.count()
yes = 100*data.mapHelp[data.mapHelp=='YES'].count()/float(total)
no = 100*data.mapHelp[data.mapHelp=='NO'].count()/float(total)
NA = 100*data.mapHelp[data.mapHelp=='NA'].count()/float(total)

objects = ('YES', 'NO', 'NA')
x_pos = np.arange(len(objects))
values = [yes, no, NA]

fig = plt.figure()
plt.bar(x_pos, values, align='center', width=0.5)
plt.xticks(x_pos, ['Yes', 'No', 'No Preference'], fontsize=ticksize, fontweight='bold')
plt.ylim([0,100])
plt.yticks(np.arange(0,101,10), fontsize=ticksize, fontweight='bold')
plt.ylabel('Percentage', fontsize=axsize)
plt.title('Navigation Help is a Priority', fontsize=tsize)
plt.grid(axis='y', linestyle='--', linewidth=1, alpha=0.5)
savePDF(figuresPDF, fig)



###########################################################################
# SECTION 3: Data Sharing Preferences (1/3)
###########################################################################
# Position
objects = []
scale = 100.0/float(data.position.count())
for i in range(1, 6):
    objects.append(data[data.position==i].position.count())
x_pos = np.arange(1, len(objects)+1)
fig = plt.figure()
plt.bar(x_pos, objects, align='center', width=0.5)
plt.xticks(x_pos, fontsize=ticksize, fontweight='bold')
plt.ylim([0,50])
plt.yticks(np.arange(0,51,5), fontsize=ticksize, fontweight='bold')
plt.xlabel('Likert Scale', fontsize=axsize)
plt.ylabel('Percentage', fontsize=axsize)
plt.title('Willingness to Share Position Data', fontsize=tsize-2)
plt.grid(axis='y', linestyle='--', linewidth=1, alpha=0.5)
savePDF(figuresPDF, fig)

# Speed
objects = []
scale = 100.0/float(data.speed.count())
for i in range(1, 6):
    objects.append(data[data.speed==i].speed.count())
x_pos = np.arange(1, len(objects)+1)
fig = plt.figure()
plt.bar(x_pos, objects, align='center', width=0.5)
plt.xticks(x_pos, fontsize=ticksize, fontweight='bold')
plt.ylim([0,50])
plt.yticks(np.arange(0,51,5), fontsize=ticksize, fontweight='bold')
plt.xlabel('Likert Scale', fontsize=axsize)
plt.ylabel('Percentage', fontsize=axsize)
plt.title('Willingness to Share Speed Data', fontsize=tsize-2)
plt.grid(axis='y', linestyle='--', linewidth=1, alpha=0.5)
savePDF(figuresPDF, fig)

# Turn Signals
objects = []
scale = 100.0/float(data.signals.count())
for i in range(1, 6):
    objects.append(data[data.signals==i].signals.count())
x_pos = np.arange(1, len(objects)+1)
fig = plt.figure()
plt.bar(x_pos, objects, align='center', width=0.5)
plt.xticks(x_pos, fontsize=ticksize, fontweight='bold')
plt.ylim([0,50])
plt.yticks(np.arange(0,51,5), fontsize=ticksize, fontweight='bold')
plt.xlabel('Likert Scale', fontsize=axsize)
plt.ylabel('Percentage', fontsize=axsize)
plt.title('Willingness to Share Signal Data', fontsize=tsize-2)
plt.grid(axis='y', linestyle='--', linewidth=1, alpha=0.5)
savePDF(figuresPDF, fig)

# Number of Passengers
objects = []
scale = 100.0/float(data.passengers.count())
for i in range(1, 6):
    objects.append(data[data.passengers==i].passengers.count())
x_pos = np.arange(1, len(objects)+1)
fig = plt.figure()
plt.bar(x_pos, objects, align='center', width=0.5)
plt.xticks(x_pos, fontsize=ticksize, fontweight='bold')
plt.ylim([0,50])
plt.yticks(np.arange(0,51,5), fontsize=ticksize, fontweight='bold')
plt.xlabel('Likert Scale', fontsize=axsize)
plt.ylabel('Percentage', fontsize=axsize)
plt.title('Willingness to Share Passenger Data', fontsize=tsize-2)
plt.grid(axis='y', linestyle='--', linewidth=1, alpha=0.5)
savePDF(figuresPDF, fig)

# Number of stops
objects = []
scale = 100.0/float(data.totalStops.count())
for i in range(1, 6):
    objects.append(data[data.totalStops==i].totalStops.count())
x_pos = np.arange(1, len(objects)+1)
fig = plt.figure()
plt.bar(x_pos, objects, align='center', width=0.5)
plt.xticks(x_pos, fontsize=ticksize, fontweight='bold')
plt.ylim([0,50])
plt.yticks(np.arange(0,51,5), fontsize=ticksize, fontweight='bold')
plt.xlabel('Likert Scale', fontsize=axsize)
plt.ylabel('Percentage', fontsize=axsize)
plt.title('Willingness to Share Stop Count Data', fontsize=tsize-2)
plt.grid(axis='y', linestyle='--', linewidth=1, alpha=0.5)
savePDF(figuresPDF, fig)

# Stop Time
objects = []
scale = 100.0/float(data.stopTime.count())
for i in range(1, 6):
    objects.append(data[data.stopTime==i].stopTime.count())
x_pos = np.arange(1, len(objects)+1)
fig = plt.figure()
plt.bar(x_pos, objects, align='center', width=0.5)
plt.xticks(x_pos, fontsize=ticksize, fontweight='bold')
plt.ylim([0,60])
plt.yticks(np.arange(0,61,5), fontsize=ticksize, fontweight='bold')
plt.xlabel('Likert Scale', fontsize=axsize)
plt.ylabel('Percentage', fontsize=axsize)
plt.title('Willingness to Share Stop Time Data', fontsize=tsize-2)
plt.grid(axis='y', linestyle='--', linewidth=1, alpha=0.5)
savePDF(figuresPDF, fig)

# Journey duration
objects = []
scale = 100.0/float(data.duration.count())
for i in range(1, 6):
    objects.append(data[data.duration==i].duration.count())
x_pos = np.arange(1, len(objects)+1)
fig = plt.figure()
plt.bar(x_pos, objects, align='center', width=0.5)
plt.xticks(x_pos, fontsize=ticksize, fontweight='bold')
plt.ylim([0,60])
plt.yticks(np.arange(0,61,5), fontsize=ticksize, fontweight='bold')
plt.xlabel('Likert Scale', fontsize=axsize)
plt.ylabel('Percentage', fontsize=axsize)
plt.title('Willingness to Share Journey Duration Data', fontsize=tsize-4)
plt.grid(axis='y', linestyle='--', linewidth=1, alpha=0.5)
savePDF(figuresPDF, fig)

# Journey length
objects = []
scale = 100.0/float(data.distance.count())
for i in range(1, 6):
    objects.append(data[data.distance==i].distance.count())
x_pos = np.arange(1, len(objects)+1)
fig = plt.figure()
plt.bar(x_pos, objects, align='center', width=0.5)
plt.xticks(x_pos, fontsize=ticksize, fontweight='bold')
plt.ylim([0,60])
plt.yticks(np.arange(0,61,5), fontsize=ticksize, fontweight='bold')
plt.xlabel('Likert Scale', fontsize=axsize)
plt.ylabel('Percentage', fontsize=axsize)
plt.title('Willingness to Share Journey Distance Data', fontsize=tsize-4)
plt.grid(axis='y', linestyle='--', linewidth=1, alpha=0.5)
savePDF(figuresPDF, fig)

# Emissions Class
objects = []
scale = 100.0/float(data.emissionClass.count())
for i in range(1, 6):
    objects.append(data[data.emissionClass==i].emissionClass.count())
x_pos = np.arange(1, len(objects)+1)
fig = plt.figure()
plt.bar(x_pos, objects, align='center', width=0.5)
plt.xticks(x_pos, fontsize=ticksize, fontweight='bold')
plt.ylim([0,60])
plt.yticks(np.arange(0,61,5), fontsize=ticksize, fontweight='bold')
plt.xlabel('Likert Scale', fontsize=axsize)
plt.ylabel('Percentage', fontsize=axsize)
plt.title('Willingness to Share Emission Class Data', fontsize=tsize-4)
plt.grid(axis='y', linestyle='--', linewidth=1, alpha=0.5)
savePDF(figuresPDF, fig)

# Vehicle Type
objects = []
scale = 100.0/float(data.vehicleType.count())
for i in range(1, 6):
    objects.append(data[data.vehicleType==i].vehicleType.count())
x_pos = np.arange(1, len(objects)+1)
fig = plt.figure()
plt.bar(x_pos, objects, align='center', width=0.5)
plt.xticks(x_pos, fontsize=ticksize, fontweight='bold')
plt.ylim([0,60])
plt.yticks(np.arange(0,61,5), fontsize=ticksize, fontweight='bold')
plt.xlabel('Likert Scale', fontsize=axsize)
plt.ylabel('Percentage', fontsize=axsize)
plt.title('Willingness to Share Vehicle Type Data', fontsize=tsize-4)
plt.grid(axis='y', linestyle='--', linewidth=1, alpha=0.5)
savePDF(figuresPDF, fig)

# Stop Factor
objects = []
scale = 100.0/float(data.speedFactor.count())
for i in range(1, 6):
    objects.append(data[data.speedFactor==i].speedFactor.count())
x_pos = np.arange(1, len(objects)+1)
fig = plt.figure()
plt.bar(x_pos, objects, align='center', width=0.5)
plt.xticks(x_pos, fontsize=ticksize, fontweight='bold')
plt.ylim([0,50])
plt.yticks(np.arange(0,51,5), fontsize=ticksize, fontweight='bold')
plt.xlabel('Likert Scale', fontsize=axsize)
plt.ylabel('Percentage', fontsize=axsize)
plt.title('Willingness to Share Speeding Data', fontsize=tsize-2)
plt.grid(axis='y', linestyle='--', linewidth=1, alpha=0.5)
savePDF(figuresPDF, fig)


###########################################################################
# SECTION 4: Data Sharing Preferences (2/3)
###########################################################################
# UTM Data Sharing Acceptance
objects = []
scale = 100.0/float(data.UTMAcceptance.count())
for i in range(1, 11):
    objects.append(data[data.UTMAcceptance==i].UTMAcceptance.count())
x_pos = np.arange(1, len(objects)+1)
fig = plt.figure()
plt.bar(x_pos, objects, align='center', width=0.5)
plt.xticks(x_pos, fontsize=ticksize, fontweight='bold')
plt.ylim([0,24])
plt.yticks(np.arange(0,25,2), fontsize=ticksize, fontweight='bold')
plt.xlabel('Likert Scale', fontsize=axsize)
plt.ylabel('Percentage', fontsize=axsize)
plt.title('UTM Data Sharing Willlingness', fontsize=tsize-2)
plt.grid(axis='y', linestyle='--', linewidth=1, alpha=0.5)
savePDF(figuresPDF, fig)
print('UTM Mean Score', data.UTMAcceptance.mean())
print('UTM Median Score', data.UTMAcceptance.median())
print('UTM Std Score', data.UTMAcceptance.std())
print('UTM Sentiment Score', 100*data.UTMAcceptance.apply(likertMap10).mean())

objects = []
data['UTMAcceptanceDS'] = ((data.UTMAcceptance/2.0)+0.1).apply(np.round).apply(int)
scale = 100.0/float(data.UTMAcceptanceDS.count())
for i in range(1, 6): 
    objects.append(data[data.UTMAcceptanceDS==i].UTMAcceptanceDS.count())
x_pos = np.arange(1, len(objects)+1)
fig = plt.figure()
plt.bar(x_pos, objects, align='center', width=0.5)
plt.xticks(x_pos, fontsize=ticksize, fontweight='bold')
plt.ylim([0,50])
plt.yticks(np.arange(0,51,5), fontsize=ticksize, fontweight='bold')
plt.xlabel('Likert Scale', fontsize=axsize)
plt.ylabel('Percentage', fontsize=axsize)
plt.title('UTM Data Sharing Willlingness', fontsize=tsize-2)
plt.grid(axis='y', linestyle='--', linewidth=1, alpha=0.5)
savePDF(figuresPDF, fig)


# Preferred Data Sharing Method
data.deliveryMode.fillna('NA', inplace=True)
objects = ['APP', 'BUILTIN', 'THIRDPARTY', 'OTHER']
labels = ['App', 'Built-in', '3rd Party', 'Other']
x_pos = np.arange(len(objects))
scale = 100.0/float(data.deliveryMode.count())
values = [data.deliveryMode[data.deliveryMode.apply(lambda y: x in y)].count()*scale for x in objects]

fig = plt.figure()
plt.bar(x_pos, values, align='center', width=0.5)
plt.xticks(x_pos, labels, fontsize=ticksize, fontweight='bold', rotation=90)
plt.ylim([0,50])
plt.yticks(np.arange(0,51,5), fontsize=ticksize, fontweight='bold')
plt.ylabel('Percentage', fontsize=axsize)
plt.title('Service Delivery Method Preference', fontsize=tsize-2)
plt.grid(axis='y', linestyle='--', linewidth=1, alpha=0.5)
savePDF(figuresPDF, fig)


###########################################################################
# SECTION 5: Data Sharing Preferences (3/3)
###########################################################################
# Mode priority
fig = plt.figure()
groups = ['busPriority', 'emergencyPriority',
          'sharedPriority', 'evPriority', 'tradePriority']
n_groups = len(groups)
YES = []
NO = []
NA = []
for group in groups:
    data[group].fillna('NA', inplace=True)

for group in groups:
    scale = 100.0/float(data[group].count())
    YES.append(scale*data[group][data[group]=='YES'].count())
    NO.append(scale*data[group][data[group]=='NO'].count())
    NA.append(scale*data[group][data[group]=='NA'].count())

# create plot
fig, ax = plt.subplots()
index = np.arange(n_groups)
bar_width = 0.25

rects1 = plt.bar(index, YES, bar_width,
color='C0',
label='Yes')

rects2 = plt.bar(index + bar_width, NO, bar_width,
color='C1',
label='No')

rects3 = plt.bar(index + 2*bar_width, NA, bar_width,
color='C7',
label='Don\'t Know')

plt.ylim([0,100])
plt.yticks(np.arange(0,101,10), fontsize=ticksize, fontweight='bold')
ax = plt.gca()
ax.yaxis.set_minor_locator(tck.MultipleLocator(5))
plt.grid(axis='y', linestyle='--', linewidth=1, alpha=0.5)
plt.grid(axis='y', linestyle=':', linewidth=1, alpha=0.5, which='minor')
plt.ylabel('Percentage', fontsize=axsize-2)
plt.title('Should These Vehicle Types Get Priority?', fontsize=tsize-4)
plt.xticks(index + bar_width, ('Bus', 'Em. Svc.', 'Shared', 'EV', 'Trade'), fontsize=ticksize, fontweight='bold', rotation=90)
plt.legend(loc='upper center', bbox_to_anchor=(0.5, 1.26), ncol=3, fontsize=axsize-4)
savePDF(figuresPDF, fig)


###########################################################################
# SECTION 6: Correlations and other Trends
###########################################################################
data.deliveryMode.fillna('NA', inplace=True)
objects = ['position', 'speed', 'signals', 'passengers', 'totalStops', 'stopTime',
           'duration', 'distance', 'emissionClass', 'vehicleType', 'speedFactor']
labels = ['Position', 'Speed', 'Signals', 'Passengers', 'Total Stops', 'Stop Time',
          'Duration', 'Distance', 'Emission Class', 'Vehicle Type', 'Speed Factor']
x_pos = np.arange(len(objects))
values = []
for col in objects:
    values.append(data[col].dropna().apply(likertMap).mean())

values= np.array(values)
colors = ['C0' if x > 0 else 'C1' for x in values]
cmapPos = cm.get_cmap('summer')
cmapNeg = cm.get_cmap('autumn')
def cmapFn(x):
    if x >= 0:
        return cmapPos(abs(1-x))
    else:
        return cmapNeg(1-abs(x))
barColors = list(map(cmapFn, 1.0*values)) # scale values to max

fig = plt.figure(figsize=(7,4))
cmapCB= matplotlib.colors.ListedColormap([cmapFn(x) for x in np.linspace(-1,1,1000)])
normCB= matplotlib.colors.Normalize(vmin=-100,vmax=100)

# Using contourf to provide my colorbar info, then clearing the figure
Z = [[0,0],[0,0]]
levels = np.arange(-100, 100.1, 0.1)
CS3 = plt.contourf(Z, levels, cmap=cmapCB)
plt.clf()

plt.bar(x_pos, 100.0*values, align='center', width=0.5, color=barColors)
plt.xticks(x_pos, labels, fontsize=ticksize, fontweight='bold', rotation=90)
plt.ylim([-20,60])
plt.yticks(np.arange(-20,61,10), fontsize=ticksize, fontweight='bold')
ax = plt.gca()
ax.yaxis.set_minor_locator(tck.MultipleLocator(5))
plt.grid(axis='y', linestyle='--', linewidth=1, alpha=0.5, which='both')
plt.ylabel('Percentage', fontsize=axsize)
plt.title('Data Sharing Sentiment Score', fontsize=tsize-2)
cbarObj = plt.colorbar(CS3, pad=0.01)
cbarObj.set_ticks(np.arange(-100,101,25))
savePDF(figuresPDF, fig)

figuresPDF.close()