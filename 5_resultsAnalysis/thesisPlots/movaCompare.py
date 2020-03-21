from glob import glob
import pandas as pd
import numpy as np

def pct(a,b):
    return 100.0*(1.0 - (a/float(b)))


files = ['/hardmem/outputCSV/GPSVA-simpleT-tripinfo.csv',
         '/hardmem/outputCSV/HVA-simpleT-tripinfo.csv',
         '/hardmem/outputCSV/GPSVAslow-simpleT-tripinfo.csv',
         '/hardmem/outputCSV/CDOTS-simpleT-1101000-tripinfo.csv',
         '/hardmem/outputCSV/CDOTSslow-simpleT-1101000-tripinfo.csv']
MOVAdelay = 20.3
cvps = np.arange(0,101, 10, dtype=int)

for file in files:
    print(file)
    df = pd.read_csv(file)
    delays = df.groupby('cvp').delay.mean()
    for cvp, delay in zip(cvps, delays):
        print(cvp, delay, pct(delay, MOVAdelay))
    print('')