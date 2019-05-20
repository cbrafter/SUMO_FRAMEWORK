#!/bin/bash
#PBS -N SIMJOB
#PBS -j oe
#PBS -l walltime=00:01:00
#PBS -l nodes=1:ppn=1
#PBS -m ae -M cbr1g15@soton.ac.uk

# Script to run SUMO simulations then parse the results when sims complete
cd /scratch/cbr1g15/SUMOsingularity
# Trigger SUMO sims
JOB_ID=$(qsub -q batch sumojob.sh)
echo $JOB_ID
# trigger result parsing dependent on success of sumo job array
qsub -W depend=afterokarray:$JOB_ID parseResults.sh

