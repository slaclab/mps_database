#!/bin/bash
export current=`pwd -P`
export PYTHONPATH="/afs/slac/g/lcls/package/anaconda/2020.11/envs/mps-environment/bin/python":$current
echo $PYTHONPATH
