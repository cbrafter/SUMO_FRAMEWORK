# -*- coding: utf-8 -*-
import sys
import os
import shutil
import time
import numpy as np
import multiprocessing as mp
from itertools import product
from glob import glob
from hpcSimulation import simulation
sys.path.insert(0, '../1_sumoAPI')
sys.path.insert(0, '../3_signalControllers')
import signalTools as sigTools
from socket import gethostname
import traceback
import random

###############################################################################
# MAIN SIMULATION DEFINITION
###############################################################################
timer = sigTools.simTimer()
timer.start()

# Test configurations, don't run TRANSYT for lo and hi cases
config = ['sellyOak_hi', 'GPSVAslow', 0.0, 9, True, 13]

# Run simualtions in parallel.
try:
    result = simulation(config, GUIbool=True)
except Exception as e:
    print(e)
    traceback.print_exc()
    sys.stdout.flush()
finally:
    timer.stop()
    # Inform of failed expermiments
    if all([r[0] for r in result]):
        print('Simulations complete, no errors, exectime: '+timer.strTime())
    else:
        print('Simulations aborted, exectime: '+timer.strTime())
        print('Failed Experiment Runs:')
        for r in result:
            if not r[0]:
                print(r[1])
