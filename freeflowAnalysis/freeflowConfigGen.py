"""
@file    sumoConfigGen.py
@author  Craig Rafter
@date    29/01/2016

Code to generate a config file for a SUMO model.

"""

def sumoConfigGen(modelname='simpleT',
                  configFile='./models/simpleT.sumocfg',
                  exportPath='../results/',
                  CVP=0,
                  stepSize=0.1,
                  run=0,
                  port=8813,
                  seed=23423):
    configData = """<configuration>
    <input>
        <net-file value="{model}.net.xml"/>
        <route-files value="../../testing/FREEFLOW_TRIPS/freeflow_{model}.rou.xml"/>
    </input>
    <output>
        <tripinfo-output value="{expPath}{model}_freeflow_tripinfo.xml"/>
    </output>
    <time>
        <begin value="0"/>
        <step-length value="{stepSz}"/>
    </time>
    <processing>
        <!--TURN OFF TELEPORTING-->
        <time-to-teleport value="-1"/>
    </processing>
    <random_number>
        <seed value="{seed}"/>
    </random_number>
    <report>
        <no-step-log value="true"/>
        <error-log value="logfile.txt"/>
    </report>
    <traci_server>
        <remote-port value="{SUMOport}"/>
    </traci_server>
""".format(model=modelname,
           expPath=exportPath,
           stepSz=stepSize,
           SUMOport=port,
           seed=seed)
    
    # write configuration to file
    with open(configFile, 'w') as f:
        f.write(configData)
        f.write("\n</configuration>\n")
