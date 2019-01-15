# EPICS database templates

This directory contains templates files used to generated EPICS DB files using the parameters of each application obtained from the MPS database.

## Generating the templates

The template files are defined as substitutions files, which can be expanded with the 'expand.sh' script. The script will take the '.substitution' files and generated '.template' files.

## List of substitution and generated template files

This is a list of substitutions files, which template files are generated from them, and a description of their use case.

Substitution File       | Generated template File  | Description
------------------------|--------------------------|------------------------------------
mps.substitutions       | mps.template             | Records commons to all analog devices.
thr_base.substitutions  | thr_base.template        | Records commons to all analog faults.
thr.substitutions       | thr.template             | Records commons to each bit in each analog fault.