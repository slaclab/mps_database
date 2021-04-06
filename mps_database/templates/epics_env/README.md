# EPICS environmental variables templates

This directory contains templates files used to generated EPICS environmental setting files using the parameters of each application obtained from the MPS database.

## List of template files

This is a list of template files and a description of their use case.

Template File                    | Description
---------------------------------|---------------------------------------------------------------------
header.template                  | Link node name and information about the MPS database
ioc_info.template                | IOC_NAME environment variable used by iocAdmin
prefix.template                  | MPS PV name prefix env variable (L2MPS_PREFIX), used by all applications.
