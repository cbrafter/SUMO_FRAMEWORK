#!/bin/bash
#PBS -N CBRSUMO
#PBS -j oe
#PBS -l walltime=0:05:00
#PBS -l nodes=1:ppn=16
#PBS -m ae -M cbr1g15@soton.ac.uk
# Script to run SUMO simulations 

# Load required modules
module load singularity/2.2.1

# Change to the working directory
cd /scratch/cbr1g15/SUMOsingularity/

# Run simulation
singularity exec -w -B ../hardmem/:/hardmem/ sumohpc.img\
    bash -c "cd ~/sumofwk/4_simulation && python iridisTest.py"
