# -*- coding: utf-8 -*-
"""
Created on Thu Feb  1 12:56:52 2018

@author: craig
"""
import xml.etree.ElementTree as ET


filename = 'Scoot_Birmingham_jan18.xml'
print('Parsing XML')
root = ET.parse(filename).getroot()
'''
print('Determining data structure')
# Get column headings
cols = []
for elem in root[0]:
    cols.append(elem.tag)
    # Add columns for attribute values, sort to make sure they are in the
    # same order every time
    keys = list(elem.attrib.keys())
    keys.sort()
    for key in keys:
        cols.append(elem.tag + '_' + key)
'''
outfile = open(filename.split('.')[0]+'.csv', 'w')
outfile.write(','.join(cols)+'\n')  # write header
print('Writing data')
first = True
for elem in ET.iterparse(filename):
    print(elem.text)
    if first:
        first = False
    else:
        break

'''
    data = []
    for elem in branch:
        value = elem.text
        data.append(value)
        # Add attribute values, sort to make sure they are in the
        # same order every time
        keys = list(elem.attrib.keys())
        keys.sort()
        for key in keys:
            data.append(elem.attrib[key])
    #print(data)
    outfile.write(','.join(data)+'\n')
'''
outfile.close()
