#!/bin/bash
#PBS -N postProcess
#PBS -j oe
#PBS -l walltime=5:00:00
#PBS -l nodes=1:ppn=16
#PBS -m ae -M cbr1g15@soton.ac.uk
# Script to run SUMO simulations

# Load required modules
module load python/3.5.1

# tidy output files
cd /scratch/cbr1g15/SUMOsingularity/
FOLDERNAME=$(ls CBRSUMO* | head -1)
mkdir $(python -c "import sys; print(sys.argv[-1].split('.')[-1])" $FOLDERNAME)

# Change to the working directory
cd ./SUMO_FRAMEWORK/5_resultsAnalysis

# Parse results
echo "-> PARSING MATS RESULTS..."
python3 splitParser.py /scratch/cbr1g15/hardmem/results/
echo "PARSING COMPLETE"

echo "-> PARSING CDOTS RESULTS..."
python3 cdotsParser.py /scratch/cbr1g15/hardmem/results/
echo "PARSING COMPLETE"

echo "Clearing temp model files..."
rm -rf SUMO_FRAMEWORK/2_models/sellyOak_*_*
echo "Temp model files cleared."
