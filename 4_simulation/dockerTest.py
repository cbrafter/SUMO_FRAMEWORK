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
from socket import gethostname
import simulation

print('Running the script! {} {}'.format(sys.argv[1], sys.argv[2]))
#os.mkdir('/hardmem/results/stuff/')
# with open('/hardmem/results/stuff/sampleT.txt', 'w') as f:
#     f.write('Hello World! {} {}'.format(sys.argv[1], sys.argv[2]))

# print(os.path.exists('/hardmem/results/stuff/'))
# print([psutil.cpu_count(), psutil.cpu_count(logical=False)])

simulation.simulation(['sellyOak_avg', 'TRANSYT', 0.1, 10])