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
    if 'selly' in modelname:
        routename = modelname
        modelname = modelname.split('_')[0]
    else:
        routename = modelname
    configData = """<configuration>
    <input>
        <net-file value="{model}.net.xml"/>
        <route-files value="/hardmem/ROUTEFILES/{route}_R{Nrun:03d}_CVP{cvp:03d}.rou.xml"/>
        <!--<gui-settings-file value="gui-settings.cfg"/>-->
        <additional-files value="{model}.det.xml"/>
    </input>
    <output>
        <!--<summary-output value="{expPath}summary_R{Nrun:03d}_CVP{cvp:03d}.xml"/>-->
        <tripinfo-output value="{expPath}tripinfo_R{Nrun:03d}_CVP{cvp:03d}.xml"/>
        <!--<vehroute-output value="{expPath}vehroute_R{Nrun:03d}_CVP{cvp:03d}.xml"/-->
        <!--queue-output value="{expPath}queuedata_R{Nrun:03d}_CVP{cvp:03d}.xml"/-->
    </output>
    <time>
        <begin value="0"/>
        <step-length value="{stepSz}"/>
    </time>
    <processing>
        <!--TURN OFF TELEPORTING-->
        <time-to-teleport value="-1"/>
        <ignore-junction-blocker value="60"/>
        <!--collision.mingap-factor value="0"/-->
        <!--no-internal-links value="true"/-->
    </processing>
    <random_number>
        <seed value="{seed}"/>
    </random_number>
    <report>
        <no-step-log value="true"/>
        <!--error-log value="logfile.txt"/-->
    </report>
    <traci_server>
        <remote-port value="{SUMOport}"/>
    </traci_server>
""".format(model=modelname,
           route=routename, 
           expPath=exportPath,
           cvp=int(CVP*100),
           stepSz=stepSize,
           Nrun=run,
           SUMOport=port,
           seed=seed)
    
    # write configuration to file
    with open(configFile, 'w') as f:
        f.write(configData)
        f.write("\n</configuration>\n")
