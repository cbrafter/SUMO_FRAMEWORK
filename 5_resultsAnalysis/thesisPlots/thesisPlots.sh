#!/bin/bash

# MATS plots
python matsDelayPlotter.py
python matsDelayPlotter.py ped
python matsStopsPlotter.py
python matsStopsPlotter.py ped
python matsEmissionPlotter.py ped
python matsStageTimeAnalysis.py

# CDOTS plots
python cdotsDelayPlotter.py
python cdotsDelayPlotter.py ped
python cdotsStopsPlotter.py
python cdotsStopsPlotter.py ped
python cdotsEmissionPlotter.py ped
python cdotsStageTimeAnalysis.py

# SYNCDOTS plots
python syncdotsDelayPlotter.py
python syncdotsDelayPlotter.py ped
python syncdotsStopsPlotter.py
python syncdotsStopsPlotter.py ped
python syncdotsEmissionPlotter.py ped
python syncdotsTimeDistancePlots.py


# trim whitespace from around the file edges
for f in $(ls *.pdf); do
    pdfcrop --margins '0 0 0 0' $f;
    mv $(basename -s ".pdf" $f)-crop.pdf $f;
done


echo "DONE"
