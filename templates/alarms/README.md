# Alarm config file templates

This directory contains templates files used to Alarm Handler alhConfig
files using the parameters obtained from the MPS database.

## Generating the templates

The script <TOP>/tools/export_alarms.py uses the template files along with
generated substitution files to create alhConfig files.

## List of substitution and generated template files

This is a list of substitutions files, which template files are generated from
them, and a description of their use case. The string 'group' in the alhConfig 
file name is substitute for the alarm groups (e.g. GUNB, BC1B, etc).

Template File(s)               | Generated alhConfig File  | Description
-------------------------------|---------------------------|------------------------------------
mps_group_header.template      | mps_group.alhConfig       | defines the alarms for the group, based on
mps_group.template             |                           | the MPS Fault PVs.
-------------------------------|---------------------------|------------------------------------
mps_group_apps_header.template | mps_group_apps.alhConfig  | defines the alarms generated when MPS
mps_group_apps.template        |                           | fails to get updates from the apps
-------------------------------|---------------------------|------------------------------------
mps_include.template           | mps.alhConfig             | defines main ALL2:MPS alarm group, that
                               |                           | contains all the groups defined above
-------------------------------|---------------------------|------------------------------------

