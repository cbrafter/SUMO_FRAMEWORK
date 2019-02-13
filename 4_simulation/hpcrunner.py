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

###############################################################################
# MAIN SIMULATION DEFINITION
###############################################################################
timer = sigTools.simTimer()
timer.start()
models = ['sellyOak_lo', 'sellyOak_avg', 'sellyOak_hi']
tlControllers = ['TRANSYT', 'GPSVA', 'GPSVAslow', 'HVA']
pedStage = [True, False]
CAVratios = np.linspace(0, 1, 11)
runIDs = [1]
PBS_ARRAYID = int(sys.argv[-1])
start = PBS_ARRAYID * 16
stop = (PBS_ARRAYID + 1) * 16

configs = []
# Generate all simulation configs for fixed time and VA
configs += list(product(models[::-1], tlControllers[:1], [0.], runIDs, pedStage))
# Generate runs for CAV dependent controllers
configs += list(product(models[:4][::-1]+models[4:],
                        tlControllers[1:], CAVratios[::-1], runIDs, pedStage))
# Test configurations
configs = list(product(models, tlControllers[:1], CAVratios[:1], runIDs, pedStage)) # 6
configs += list(product(models, tlControllers[1:], CAVratios, runIDs, pedStage)) # 198

#sort configurations to process most intensive case first
configs.sort(key=lambda x: x[0], reverse=False)
if stop >= len(configs):
    configs = configs[start:]
else:
    configs = configs[start:stop]
# run in descending CAV ratio
print('# simulations: '+str(len(configs)))

nproc = 16
for i in range(len(configs)):
    configs[i] = list(configs[i])
    configs[i].append(i)

print('Starting simulation on {} cores'.format(nproc)+' '+time.ctime())
# define work pool
workpool = mp.Pool(processes=nproc)
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
    if all([r[0] for r in result]):
        print('Simulations complete, no errors, exectime: '+timer.strTime())
    else:
        print('Simulations aborted, exectime: '+timer.strTime())
        print('Failed Experiment Runs:')
        for r in result:
            if not r[0]:
                print(r[1])
