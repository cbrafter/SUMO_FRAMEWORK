# -*- coding: utf-8 -*-
import sys
import os
import shutil
import time
import numpy as np
import multiprocessing as mp
import itertools
from glob import glob
from simulation import simulation
sys.path.insert(0, '../1_sumoAPI')
sys.path.insert(0, '../3_signalControllers')
import signalTools as sigTools

###############################################################################
# MAIN SIMULATION DEFINITION
###############################################################################
timer = sigTools.simTimer()
timer.start()
models = ['cross', 'simpleT', 'twinT', 'corridor',
          'sellyOak_lo', 'sellyOak_avg', 'sellyOak_hi']
tlControllers = ['fixedTime', 'HVA', 'GPSVA', 'HVAslow', 'GPSVAslow']
CAVratios = np.linspace(0, 1, 11)

if len(sys.argv) >= 3:
    runArgs = sys.argv[1:3]
    runArgs = [int(arg) for arg in runArgs]
    runArgs.sort()
    runStart, runEnd = runArgs
else:
    runStart, runEnd = [1, 11]

runIDs = np.arange(runStart, runEnd)

configs = []
# Generate all simulation configs for fixed time and VA
configs += list(itertools.product(models[::-1],
                                  tlControllers[:1],
                                  [0.],
                                  runIDs))
# Generate runs for CAV dependent controllers
configs += list(itertools.product(models[:4][::-1]+models[4:],
                                  tlControllers[1:],
                                  CAVratios[::-1],
                                  runIDs))
# Test configurations
#configs = list(itertools.product(models, tlControllers[:1], CAVratios[:1], runIDs))
configs = list(itertools.product(models[:1],
                                 tlControllers[:1],
                                 CAVratios[:1],
                                 runIDs[:2]))
print('# simulations: '+str(len(configs)))

# nproc = sigTools.getNproc('best')
nproc = 7
print('Starting simulation on {} cores'.format(nproc)+' '+time.ctime())
# define work pool
workpool = mp.Pool(processes=nproc)
# Run simualtions in parallel
result = workpool.map(simulation, configs, chunksize=1)
# remove spawned model copies
for rmdir in glob('../2_models/*_*'):
    if os.path.isdir(rmdir):
        shutil.rmtree(rmdir)

timer.stop()
# Inform of failed expermiments
if all(result):
    print('Simulations complete, no errors, exectime: '+timer.strTime())
else:
    print('Failed Experiment Runs:')
    for i, j in zip(configs, result):
        if not j:
            print(i)
