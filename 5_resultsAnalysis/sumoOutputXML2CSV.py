# -*- coding: utf-8 -*-
"""
Created on Tue Apr 17 14:12:48 2018

@author: craig
"""

import re
import os

def xml2csv(infile, outfile=None):
    if outfile == None:
        outfile = os.path.splitext(infile) + 'csv'
    fileName = os.path.split(infile)[-1]
    fields = ["id", "depart", "departSpeed", "departDelay", "arrival",
              "arrivalLane", "arrivalPos", "arrivalSpeed", "duration",
              "routeLength", "waitSteps", "timeLoss", "vType"]
