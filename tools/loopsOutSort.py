# -*- coding: utf-8 -*-
"""
Created on Thu Jun 14 13:19:07 2018

@author: craig
"""
import re

path = '/home/craig/Dropbox/Craig Rafter [Integrating Automated Vehicles into the Transport Network]/SUMO_FRAMEWORK/2_models/sellyOakFlows/'
with open(path+'loops.out', 'r') as file:
    lines = file.readlines()

data = []

for line in lines:
    if re.match('.*?<interval',  line):
        data.append(line.strip())


def filter(x):
    keyA = re.search('id="(in|out)(.+?)" ', x).groups()
    keyB = float(x.split()[1].split('=')[1][1:-1])
    return (keyA[0], int(keyA[1]), keyB)

data.sort(key=filter)
lines = []
for line in data:
    begin = re.search('begin="(.+?)"', line).groups()[0]
    end = re.search('end="(.+?)"', line).groups()[0]
    line = re.sub(begin, str(int(float(begin)/3600.0)), line, count=1)
    print(line)
    line = re.sub(end, str(int(float(end)/3600.0)), line, count=1)
    print(line)
    line = line.split()
    lines.append(' '.join(line[:4]+line[5:-1])+'/>')

with open(path+'loopsSorted.xml', 'w') as file:
    file.write('\n'.join(lines))
