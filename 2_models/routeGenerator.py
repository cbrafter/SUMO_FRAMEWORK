# -*- coding: utf-8 -*-

import itertools
import numpy as np
import subprocess
import shlex
import re
import multiprocessing as mp
import time


def vehicleDistribution(cvp):
    Pcar = 82.7
    Pmoto = 3.0
    Plgv = 12.3
    Phgv = 1.6
    Pbus = 0.4
    vtype = """    <vTypeDistribution id="vDist">
        <!--PASSENGER CAR-->
        <vType id="car" length="4.3" minGap="2.5"
            accel="2.6" decel="4.5" sigma="0.5" maxSpeed="50"
            probability="{car}" color="240,228,66"/>
        <vType id="c_car" length="4.3" minGap="2.5"
            accel="2.6" decel="4.5" sigma="0.5" maxSpeed="50"
            probability="{ccar}" color="240,228,66"/>
        <!--MOTORCYCLE-->
        <vType id="motorcycle" length="2.2" minGap="2.5"
            accel="5.0" decel="9.0" sigma="0.5" maxSpeed="55"
            probability="{moto}" color="36,255,36"/>
        <vType id="c_motorcycle" length="2.2" minGap="2.5"
            accel="5.0" decel="9.0" sigma="0.5" maxSpeed="55"
            probability="{cmoto}" color="36,255,36"/>
        <!--LGV-->
        <vType id="lgv" length="6.5" minGap="2.5"
            accel="2.0" decel="4.0" sigma="0.5" maxSpeed="44"
            probability="{lgv}" color="86,180,233"/>
        <vType id="c_lgv" length="6.5" minGap="2.5"
            accel="2.0" decel="4.0" sigma="0.5" maxSpeed="44"
            probability="{clgv}" color="86,180,233"/>
        <!--HGV-->
        <vType id="hgv" length="7.1" minGap="2.5"
            accel="1.3" decel="3.5" sigma="0.5" maxSpeed="36"
            probability="{hgv}" color="0,158,115"/>
        <vType id="c_hgv" length="7.1" minGap="2.5"
            accel="1.3" decel="3.5" sigma="0.5" maxSpeed="36"
            probability="{chgv}" color="0,158,115"/>
        <!--BUS-->
        <vType id="bus" length="12.0" minGap="2.5"
            accel="1.0" decel="3.5" sigma="0.5" maxSpeed="24"
            probability="{bus}" color="255,109,182"/>
        <vType id="c_bus" length="12.0" minGap="2.5"
            accel="1.0" decel="3.5" sigma="0.5" maxSpeed="24"
            probability="{cbus}" color="255,109,182"/>
    </vTypeDistribution>
""".format(car=Pcar*(1-cvp/100.0),
           ccar=Pcar*cvp/100.0,
           moto=Pmoto*(1-cvp/100.0),
           cmoto=Pmoto*cvp/100.0,
           lgv=Plgv*(1-cvp/100.0),
           clgv=Plgv*cvp/100.0,
           hgv=Phgv*(1-cvp/100.0),
           chgv=Phgv*cvp/100.0,
           bus=Pbus*(1-cvp/100.0),
           cbus=Pbus*cvp/100.0)
    return vtype


def makeRoutes(config):
    flowPrefix, run = config
    model = flowPrefix if 'selly' not in flowPrefix else 'sellyOak'
    cvpRatios = np.linspace(0, 100, 21).astype(int)

    flowFile = './FLOWFILES/{}_flows.xml'.format(flowPrefix)
    routeFile = '/hardmem/ROUTEFILES/{}_R{:03d}.rou.xml'.format(flowPrefix,
                                                                run)

    command = 'duarouter '\
              '--route-files {} '.format(flowFile) +\
              '-n ./{m}/{m}.net.xml '.format(m=model) +\
              '-o {} --randomize-flows --seed {} '.format(routeFile, run) +\
              '--departlane "best" --departspeed "max"'
    p = subprocess.call(shlex.split(command))
    if p > 0:
        print('ERROR: DUAROUTER could not process:\n\t' + command)

    # get route file and insert vehicle type distribution and references
    # in the trips
    with open(routeFile, 'r') as f:
        content = f.readlines()

    for cvp in cvpRatios:
        finalFile = '/hardmem/ROUTEFILES/{}_R{:03d}_CVP{:03d}.rou.xml'\
            .format(flowPrefix, run, cvp)
        with open(finalFile, 'w') as f:
            for line in content:
                f.write(re.sub('<vehicle', '<vehicle type="vDist"', line))
                if '<routes' in line:
                    f.write(vehicleDistribution(cvp))

models = ['cross', 'simpleT', 'twinT', 'corridor',
          'sellyOak_avg', 'sellyOak_hi', 'sellyOak_lo']
runs = 100
configs = itertools.product(models, range(runs))
nproc = 7
print('Starting route building on {} cores'.format(nproc)+' '+time.ctime())
# define work pool
workpool = mp.Pool(processes=nproc)
# Run simualtions in parallel
result = workpool.map(makeRoutes, configs, chunksize=20)
print('DONE: '+time.ctime())
