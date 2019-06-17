# -*- coding: utf-8 -*-
import sys
import os
import shutil
import time
import numpy as np
import multiprocessing as mp
from itertools import product
from glob import glob
from optSimulation import optimiser
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
models = ['sellyOak_lo', 'sellyOak_avg', 'sellyOak_hi']
tlControllers = ['TRANSYT', 'GPSVA', 'GPSVAslow', 'HVA', 'CDOTS', 'CDOTSslow']
pedStage = [True, False]
CAVratios = np.linspace(0, 1, 11)
runIDs = list(range(1,51))
activationArrays = list(product(*([[1]]*1+[[0,1]]*6)))
nproc = 7

configs = []
# modelName, tlLogic, CVP, run, pedStage, (activationArray), procID
# CDOTS configurations
configs = [['sellyOak_avg', 'CDOTS', 1.0, 1, False, activationArrays[-1], 1],
           ['sellyOak_avg', 'CDOTSslow', 1.0, 1, False, activationArrays[-1], 2],
           ['sellyOak_avg', 'CDOTS', 0.5, 1, False, activationArrays[-1], 3],
           ['sellyOak_avg', 'CDOTSslow', 0.5, 1, False, activationArrays[-1], 4],
           ['sellyOak_avg', 'CDOTS', 0.1, 1, False, activationArrays[-1], 5],
           ['sellyOak_avg', 'CDOTSslow', 0.1, 1, False, activationArrays[-1], 6],]

#sort configurations to process most intensive case first
# configs.sort(key=lambda x: x[3], reverse=False)
# randomise configs so that long running jobs aren't bunched

print('# simulations: '+str(len(configs)))
# define work pool
nproc = min(nproc, len(configs))
workpool = mp.Pool(processes=nproc)
print('Starting simulation on {} cores'.format(nproc)+' '+time.ctime())
# Run simualtions in parallel.
try:
    result = workpool.map(optimiser, configs, chunksize=1)
    for r in results: print(r)
except Exception as e:
    print(e)
    traceback.print_exc()
    sys.stdout.flush()
finally:
    # remove spawned model copies
    # for rmdir in glob('../2_models/*_*'):
    #     try:
    #         if os.path.isdir(rmdir):
    #             shutil.rmtree(rmdir)
    #     except:
    #         pass
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