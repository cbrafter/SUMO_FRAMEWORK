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
activationArrays = list(product(*([[1]]*1+[[0,1]]*6)))

# Test configurations
# modelName, tlLogic, CVP, run, pedStage, (activationArray), procID
#config = ['sellyOak_lo', 'GPSVA', 1.0, 1, True, 5]
#config = ['sellyOak_hi', 'TRANSYT', 0.0, 1, True, 9]
config = ['simpleT', 'GPSVA', 1.0, 1, True, 9]
config = ['simpleT', 'CDOTS', 1.0, 1, False, (1,1,0,1,0,0,0), 9]

# Run simualtions in parallel.
try:
    result = simulation(config, GUIbool=False)
except Exception as e:
    print(e)
    traceback.print_exc()
    sys.stdout.flush()
finally:
    timer.stop()
    # Inform of failed expermiments
    print('Simulations complete, exectime: '+timer.strTime())
