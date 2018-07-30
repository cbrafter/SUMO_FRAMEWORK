# -*- coding: utf-8 -*-
import sys
import os
import shutil
import time
import numpy as np
import multiprocessing as mp
from itertools import product
from glob import glob
from simulation import simulation
sys.path.insert(0, '../1_sumoAPI')
sys.path.insert(0, '../3_signalControllers')
import signalTools as sigTools
from socket import gethostname

###############################################################################
# MAIN SIMULATION DEFINITION
###############################################################################
timer = sigTools.simTimer()
timer.start()
models = ['cross', 'simpleT', 'twinT', 'corridor',
          'sellyOak_lo', 'sellyOak_avg', 'sellyOak_hi']
tlControllers = ['TRANSYT', 'GPSVA', 'GPSVAslow']
CAVratios = np.linspace(0, 1, 11)

if len(sys.argv) >= 3:
    runArgs = sys.argv[1:3]
    runArgs = [int(arg) for arg in runArgs]
    runStart, runEnd = sorted(runArgs)
else:
    runStart, runEnd = [1, 11]

runIDs = np.arange(runStart, runEnd)

configs = []
# Generate all simulation configs for fixed time and VA
configs += list(product(models[::-1], tlControllers[:1], [0.], runIDs))
# Generate runs for CAV dependent controllers
configs += list(product(models[:4][::-1]+models[4:],
                        tlControllers[1:], CAVratios[::-1], runIDs))
# Test configurations
#configs = list(product(models[-3:], tlControllers[:1], CAVratios[:1], runIDs))
#configs += list(product(models[-3:], tlControllers[1:], CAVratios,  runIDs))
#configs += list(product(models[-3:], ['HVA'], CAVratios, runIDs))
configs = [('sellyOak_lo', 'GPSVAslow', 0.2, 6),
           ('sellyOak_lo', 'HVA', 0.0, 8),
           ('sellyOak_lo', 'HVA', 0.0, 10)]


configs.sort(key=lambda x: x[2], reverse=True)
# run in descending CAV ratio
print('# simulations: '+str(len(configs)))

# nproc = sigTools.getNproc('best')
nproc = 46 if 'orange' in gethostname() else 7
nproc = min(nproc, len(configs))

print('Starting simulation on {} cores'.format(nproc)+' '+time.ctime())
# define work pool
workpool = mp.Pool(processes=nproc)
# Run simualtions in parallel
try:
    result = workpool.map(simulation, configs, chunksize=1)
except Exception as e:
    print(e)
    sys.stdout.flush()
finally:
    # remove spawned model copies
    for rmdir in glob('../2_models/*_*'):
        try:
            if os.path.isdir(rmdir):
                shutil.rmtree(rmdir)
        except:
            pass
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
