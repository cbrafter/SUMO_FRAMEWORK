#!/bin/bash
#PBS -N CBRSUMO
#PBS -j oe
#PBS -l walltime=0:01:00
#PBS -l nodes=2:ppn=16
#PBS -m ae -M cbr1g15@soton.ac.uk
#PBS -t 1,2,3,4,5,6,7,8,9,11,22,33,44,55,66,77,88,99,111,222,333,444,555,666,777,888,999
# Script to run SUMO simulations 

# Load required modules
module load singularity/2.2.1

# Change to the working directory
cd /scratch/cbr1g15/SUMOsingularity/

# Run simulation
singularity exec -w -B ../hardmem/:/hardmem/ sumohpc.img\
    bash -c "cd ~/sumofwk/4_simulation && python iridisTest.py"
