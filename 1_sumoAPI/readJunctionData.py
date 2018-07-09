#!/usr/bin/env python
"""
@file    readJunctionData.py
@author  Simon Box
@date    31/01/2013

Class for reading a jcn.xml file and storing junctionObj and stageObj data.
//TODO join this class with 'readEdges' as common children of an abstract readXML class 
"""

import xml.etree.ElementTree as ET
from stageObj import stageObj
from junctionObj import junctionObj

class readJunctionData:
    
    def __init__(self, fileName):
        self.filename = fileName
        tree = ET.parse(fileName)
        root = tree.getroot()
        self.junctionList = root.getchildren()

    def getJunctionData(self):    
        junctionData = []
        
        if self.filename.split('.')[-2] != 't15':
            for junction in self.junctionList:
                stageData=[]
                for stage in junction.getchildren():
                    stageData.append(stageObj.stageObj(stage.attrib['id'],
                                                       stage.attrib['controlString'],
                                                       float(stage.attrib['period'])))
                
                junctionData.append(junctionObj(junction.attrib['id'],
                                                stageData,
                                                float(junction.attrib['offset'])))
        else:
            data = {j.attrib['id'].split('_')[0]: {} for j in self.junctionList}

            for junction in self.junctionList:
                juncID, juncMode = j.attrib['id'].split('_')
                stageData=[]
                for stage in junction.getchildren():
                    stageData.append(stageObj(stage.attrib['id'],
                                              stage.attrib['controlString'],
                                              float(stage.attrib['period'])))
                data[juncID][juncMode] = stageData
            
            for jID in data.keys():   
                junctionData.append(junctionObj.junctionObj(jID, data[jID], 0.0))

        return junctionData
