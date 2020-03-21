# -*- coding: utf-8 -*-
import sys
import os
import shutil
import time
import numpy as np
import multiprocessing as mp
from itertools import product
from glob import glob
#from optSimulation import optimiser, simulation
from timingSimulation import simulation
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
CAVratios = [0.0, 0.1, 0.5, 1.0]
runIDs = list(range(1,6))
activationArrays = list(product(*([[1]]*1+[[0,1]]*6)))
nproc = 2

configs = []

for i in range(6,11):
    configs.append(['sellyOak_hi', 'TRANSYT', 1.0, i, True])
    #configs.append(['sellyOak_hi', 'CDOTS', 1.0, i, True, (1,1,0,1,0,0,0)])
    #configs.append(['sellyOak_hi', 'CDOTSslow', 1.0, i, True, (1,1,0,1,0,0,0)])

nproc2 = nproc*nproc
for i in range(len(configs)):
    configs[i] = list(configs[i])
    configs[i].append(i)
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
    result = workpool.map(simulation, configs, chunksize=1)
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
    print('Simulations complete, exectime: '+timer.strTime())
    for i, r in enumerate(result):
        print(configs[i], r)
