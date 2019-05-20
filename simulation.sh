#!/bin/bash
# Script to run SUMO simulations then run post processing when sims complete
cd /scratch/cbr1g15/SUMOsingularity
# Trigger SUMO sims
JOB_ID=$(qsub -q batch sumojob.sh)
echo $JOB_ID
# trigger result parsing dependent on success of sumo job array
qsub -W depend=afterokarray:$JOB_ID postProcessing.sh

