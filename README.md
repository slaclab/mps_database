# LCLS-II MPS Database

This package contains `SQLAlchemy` python classes that provide access to the MPS `sqlite3` database. The classes are listed under the models subdirectory

## Initialization

In order to use mps_database, you must first have access to conda, the virtual environment and package manager. 

If you are already able to sucessfully run conda via the command line, then you can skip the "Initializing Conda" steps. This can be tested by running `conda` and comparing the following output:
```
$ conda
usage: conda [-h] [-V] command ...

conda is a tool for managing and deploying applications, environments and packages.
...
```

### Initializing Conda

Refer to documentation about using conda at SLAC.

### Creating the Conda Environment

On `lcls-dev3`, after cloning the repo (`$ git clone git@github.com:slaclab/mps_database.git`) please navigate to the top of the mps_database directory, where environment.yml is located.


Then, run the following commands to create the proper python-based virtual environment:

```
$ conda env create -f environment.yml

$ conda activate mps-environment
```
This creates a conda environment based off of the template file environment.yml. This .yml file includes a list of all packages and modules with their associated versions that will be installed within your conda environment. 

You should now be within the created conda environment with a prompt such as:

`(mps-environment) jsmith@lcls-dev3 mps_database]$`

### Initializing the Project
Now, we must initialize the mps_database module itself. In the top directory where the `setup.py` file is located, run:
```
$ pip install -e .
```
and look for the output:
```
Installing collected packages: mps-database
  Running setup.py develop for mps-database
Successfully installed mps-database
```
Note: these steps only need to be completed once. After being initialized for the first time, refer to "Standard Operation" to utilize the environment.

### Installing Packages

Should you need to install any further packages to this environment, you can do so by running `conda install packagename` with the optional source location parameter. Sample package installations include:
```
(mps-environment) $ conda install packagename
(mps-environment) $ conda install -c conda-forge packagename
```
### Deleting the Environment

If you ever need to delete the virtual environment, you can do so by running:

`conda env remove --name mps-environment`

However, you will have to create a new copy of the environment from the environment.yml file all over again. You should never need to delete this environment. 

## Operation
### Environment Setup

In order to use this module, you must be within the conda virtual environment. 


To activate the created environment, run:

`$ conda activate mps-environment`

To turn off this environment and return to your standard environment and paths, run:

`(mps-environment) $ conda deactivate`
## Scripts

All the following operations are invoked by the `mps_database/tools/export_all.py` script when creating new databases. 

### Generate Configuration database

This script creates the file sqlite file `mps_config_imported.db`, the configuration database, that is used by other scripts to generate EPICS database and panels. It also creates the file `mps_config_imported_runtime.db`, the runtime database, used by the [MPS manager](https://github.com/slaclab/mps_manager).

```
$ ./import/import-csv.py
```

### Generate All files

This export the sqlite configuration database to all other files needed to run the system.  It generates central node configuration YAML files, pydm display files, epics DB files for link nodes and central nodes.  In the near future, it will also generate documentation and alarms.  Necessary arguments:

--db <database_file>
--template <path to templates>
--destination <path to output>

```
$ ./tools/export_all.py --db <sqlite db file> --dest <destination path> --template <path to templates, located in mps_database>
```
The link node databases will be generated in <destination path> with the following structure:

```
<destination_path>/link_node_db/app_db/<CPU_NAME>/<CRATE_ID>/<SLOT_NUMBER>
```

Each directory will contain the following EPICS database and configuration files for each application:
- `mps.db`: EPICS database file
- `mps.env`: EPICS environmental variables
- `config.yaml`: Firmware configuration file

Example of the result obtained for the EIC configuration:

```
.
└── app_db
    └── cpu-gunb0-mp01
        └── 0001
            ├── 02
            │   ├── config.yaml
            │   ├── mps.db
            │   └── mps.env
            ├── 03
            │   ├── config.yaml
            │   ├── mps.db
            │   └── mps.env
            ├── 06
            │   ├── config.yaml
            │   ├── mps.db
            │   └── mps.env
            └── 07
                ├── config.yaml
                ├── mps.db
                └── mps.env
```

The central node is a collection of 3 central nodes:
cn1 = slot2 of B005-510 and handles LN groups 0-11
cn2 = slot3 of B005-510 and handles LN groups 12-23
cn3 = slot2 of L2KA00-XX and handles LN groups 0-8

The script generates files like:

<destination path>/central_node_db/cn#/<database_file>

The central node IOC will load the correct databases based on it's configuration

There are three central node configuration yaml files also created, one for each CN.  They are output to 
<destination path>/<db_name>-cn#-<db_version>.yaml.  They must be loaded into the proper CN via caput:
caput SIOC:SYS0:MP0#:CONFIG_LOAD "<proper_yaml_file>
In the future, this will be automated, but for now is by hand.

## Import CSV data

The script [import/import-csv.py](import/import-csv.py) generates a database using csv exported files from the `MPSInputList.xlsx` file (available from sharepoint). The generated database name is `mps_config_imported.db`.

###### currently depricated ######
## Tests

The [central_node_test.py](tools/central_node_test.py) script can be used to simulate firmware input data to the central node software. It sends update messages to the central node for each device state (e.g. valve on/valve off) and gets back a mitigation message, which is compared to the expected mitigation as described in the database.

The central node software must be compiled without the option `-DFW_ENABLE`, which enables the software to receive updates and send mitigation to the test script instead of exchanging messages with the central node firmware (via CPSW). The central node software can run as a standalone server (see [central_node_engine](https://github.com/slaclab/central_node_engine) package under `src/test/central_node_engine_server`). The central node IOC may also be used for testing, but it must be linked against the non-FW_ENABLED central_node_engine lib.

Options for the script are:
```
$ ./tools/central_node_test.py -h
usage: central_node_test.py [-h] [--host hostname] [--port [size]]
                            [--debug [debug]] [--device [device]] [--analog]
                            [--report] [--delay]
                            db

Send link node update to central_node_engine server

positional arguments:
  db                 database file name (e.g. mps_gun.db)

optional arguments:
  -h, --help         show this help message and exit
  --host hostname    Central node hostname
  --port [size]      server port (default=4356)
  --debug [debug]    set debug level output (default level 0)
  --device [device]  device id (default - test all digital devices)
  --analog           analog device
  --report           generate pdf report
  --delay            add 1 second delay between tests
```

Example of output:
```
$ ./tools/central_node_test.py mps_gun_config.db --host cpu-li00-mp01
YAG01B PASSED
Gun Temperature PASSED
Waveguide Temperature PASSED
BUN1B Buncher Temperature PASSED
SOL01B Temp PASSED
SOL02B Temp PASSED
VVR01 PASSED
VVR02 PASSED
```

Example of verbose output, specifying a single device for testing:
```
$ ./tools/central_node_test.py mps_gun_config.db --host cpu-li00-mp01 --device 1 --debug 1
+------------------------------------------------------------+
Device YAG01B
+------------------------------------------------------------+
Device value    : 00
Inputs          : OUT_LMTSW=0 IN_LMTSW=0
Mitigation      : MS=0 AOM=0
Recvd Mitigation: MS=0 AOM=0
+------------------------------------------------------------+
Device value    : 01
Inputs          : OUT_LMTSW=1 IN_LMTSW=0
Mitigation      : MS=2 AOM=1
Recvd Mitigation: MS=2 AOM=1
+------------------------------------------------------------+
Device value    : 02
Inputs          : OUT_LMTSW=0 IN_LMTSW=1
Mitigation      : MS=2 AOM=2
Recvd Mitigation: MS=2 AOM=2
+------------------------------------------------------------+
Device value    : 03
Inputs          : OUT_LMTSW=1 IN_LMTSW=1
Mitigation      : MS=0 AOM=0
Recvd Mitigation: MS=0 AOM=0
+------------------------------------------------------------+
YAG01B PASSED
```
