#!/bin/bash
#PBS -N CBRSUMO
#PBS -j oe
#PBS -l walltime=12:00:00
#PBS -l nodes=1:ppn=16
#PBS -m ae -M cbr1g15@soton.ac.uk
#PBS -t 0-12
# Script to run SUMO simulations 

# Load required modules
module load singularity/2.2.1

# Change to the working directory
cd /scratch/cbr1g15/SUMOsingularity/

# Run simulation
singularity exec -w \
    -B ../hardmem/:/hardmem/ \
    -B ./SUMO_FRAMEWORK/:/home/cbr1g15/sumofwk \
    sumohpc.img \
    bash -c "cd ~/sumofwk/4_simulation && python hpcrunner.py $PBS_ARRAYID"
