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
models = ['sellyOak_lo', 'sellyOak_avg', 'sellyOak_hi']
tlControllers = ['TRANSYT', 'GPSVA', 'GPSVAslow', 'HVA',
                 'CDOTS', 'CDOTSslow', 'SynCDOTS', 'SynCDOTSslow']
pedStage = [True, False]
CAVratios = np.linspace(0, 1, 11)
runIDs = list(range(31,51))
activationArrays = list(product(*([[1]]*1+[[0,1]]*6))) # All 7-bit arrays
activationArrays = [(1,1,1,1,0,0,1), # Top 5 both
                    (1,1,0,1,0,0,1), # Top 4 CDOTS
                    (1,1,1,1,0,0,0), # Top 4 CDOTSslow
                    (1,1,0,1,0,0,0)] # Top 3 both
syncFactors = [0.25, 0.5, 0.75, 1.0]
syncModes = ['PS','P','Ps']
#activationArrays = [a for a in activationArrays if not a[-1]]
PBS_ARRAYID = int(sys.argv[-1])
nproc = 16
nsims = 32
startIndex = PBS_ARRAYID * nsims
stopIndex = (PBS_ARRAYID + 1) * nsims

configs = []
# TRANSYT configurations
#configs += list(product(models, ['TRANSYT'], CAVratios[:1], runIDs, pedStage)) # 2
# MATS configurations
#configs += list(product(models, ['GPSVA', 'GPSVAslow', 'HVA'], CAVratios, runIDs, pedStage)) # 198
# CDOTS configurations
#configs += list(product(models, ['CDOTS', 'CDOTSslow'], CAVratios,
#                        runIDs, pedStage, activationArrays))
# configs = list(product(['sellyOak_avg'], tlControllers[:1], CAVratios[:1], runIDs, pedStage))
# configs += list(product(['sellyOak_avg'], tlControllers[1:], CAVratios, runIDs, pedStage))
configs += list(product(models, ['SynCDOTS', 'SynCDOTSslow'], CAVratios, runIDs, 
                       pedStage, activationArrays[-1:], syncFactors, syncModes[:1]))
# sort configurations to process most intensive case first
# configs.sort(key=lambda x: x[3], reverse=False)
# randomise configs so that long running jobs aren't bunched
random.seed(1)
random.shuffle(configs)

if stopIndex >= len(configs):
    if startIndex >= len(configs):
        print("PBS_ARRAYID indexes beyond #configs")
        sys.exit()
    configs = configs[startIndex:]
else:
    configs = configs[startIndex:stopIndex]

for i in range(len(configs)):
    configs[i] = list(configs[i])
    configs[i].append(i%nsims)

print('# simulations: '+str(len(configs)))
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
