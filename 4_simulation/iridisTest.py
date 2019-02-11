import multiprocessing as mp
from socket import gethostname
import psutil as ps
import sys
import time

def nodeTest(x):
    try:
        procID = int(mp.current_process().name.split('-')[-1])
    except:
        procID = 1
    time.sleep(2)
    return "{:2d}: {}/{} of {}".format(x, gethostname(), procID, ps.cpu_count())

#workpool = mp.Pool(processes=ps.cpu_count())
#result = workpool.map(nodeTest, range(500), chunksize=1)
#result.sort(key=lambda x: int(x.split(':')[0]))
result = nodeTest(int(sys.argv[1]))
print('\n'.join(result))
