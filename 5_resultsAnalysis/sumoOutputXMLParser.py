import re
from glob import glob
import datetime as dt
import numpy as np
from matplotlib import pyplot

resultsPath = '../../SUMO_Birmingham/sumo_model/results/'
files = glob(resultsPath + '*.xml')

regex = '<tripinfo .+? depart="(.+?)" .+? departDelay="(.+?)" .+? duration="(.+?)" .+? timeLoss="(.+?)"'

for file in files:
    outFileName = file[:-3] + 'csv'
    with open(file, 'r') as inFile, open(outFileName, 'w') as outFile:
        outFile.write('insertTime,duration,timeLoss\n')
        for line in inFile.readlines():
            if '<tripinfo ' in line:
                data = re.match(regex, line.strip()).groups()
                data = [float(x) for x in data]
                insertTime = data[0]
                duration = data[1] + data[2]
                timeLoss = data[3]
                writeData = ','.join(map(str, [insertTime,
                                               duration,
                                               timeLoss]))
                outFile.write(writeData+'\n')

# make time series
tstep = dt.timedelta(seconds=900)  # 15 minutes
# Generate each 15 min point throughout the day
timeList = [str(i*tstep) for i in range(96)]
secList = [(i*tstep).total_seconds() for i in range(96)]
timeList.append('23:59:59')  # last second of the day
secList.append(secList[-1] + 899)

files = glob(resultsPath + '*.csv')
fig1 = pyplot.figure(figsize=[14.5623058987, 9])
fig2 = pyplot.figure(figsize=[14.5623058987, 9])
for file in files:
    data = np.loadtxt(file, delimiter=',', skiprows=1)
    travelTimeData = []
    timeLossData = []
    for start, stop in zip(secList[:-1], secList[1:]):
        timeSlice = data[(data[:, 0] >= start) & (data[:, 0] < stop)]
        mean = np.mean(timeSlice, axis=0)
        travelTimeData.append(mean[1])
        timeLossData.append(mean[2])

    pyplot.figure(fig1.number)
    pyplot.plot(travelTimeData)
    pyplot.legend(['Avg Flow', 'High Flow'], fontsize=14)
    pyplot.xticks(list(range(0, 96, 4)), timeList[0:-1:4],
                  rotation=90, ma='right')
    pyplot.title('Average Travel Time', fontsize=18)
    pyplot.xlabel('Time Of Day', fontsize=16)
    pyplot.ylabel('Travel Time [s]', fontsize=16)
    pyplot.grid()
    pyplot.savefig(resultsPath+'travelTime.pdf', dpi=600)

    pyplot.figure(fig2.number)
    pyplot.plot(timeLossData)
    pyplot.legend(['Avg Flow', 'High Flow'], fontsize=14)
    pyplot.xticks(list(range(0, 96, 4)), timeList[0:-1:4],
                  rotation=90, ma='right')
    pyplot.title('Average Time Loss', fontsize=18)
    pyplot.xlabel('Time Of Day', fontsize=16)
    pyplot.ylabel('Lost Time [s]', fontsize=16)
    pyplot.grid()
    pyplot.savefig(resultsPath+'timeLoss.pdf', dpi=600)

print('~DONE~')