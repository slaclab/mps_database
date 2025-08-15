#!/bin/bash

source /afs/slac/g/lcls/epics/setup/envSet_prodOnDev.bash
echo "[INFO] EPICS production environment loaded."

export current=`pwd -P`
export PYTHONPATH=$current:"/afs/slac/g/lcls/package/anaconda/2020.11/envs/mps-environment/bin/python":
echo $PYTHONPATH

echo "Opening crate_info_display.py (y/n)?"
read -r ANSWER
if [ {$ANSWER,,} == y ]; then
	echo "[INFO] Launching PyDM..."
	pydm crate_info_display.py &
else
	echo "[INFO] Launch canceled."
fi
