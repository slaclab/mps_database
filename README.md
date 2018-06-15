LCLS-II MPS Database 
--------------------

This package contains SQLAlchemy python classes that provide access to the
MPS sqlite3 database. The classes are listed under the models subdirectory

Instructions
------------

On lcls-dev3, after cloning the repo (git clone git@github.com:slaclab/mps_database.git)
please source the following script to create the proper python virtual environment:

```
. setup.sh install
```

This has to be done only one time. However whenever opening a new session/shell please
run:

```
. setup.sh
```

to activate the virtual environment.


Scripts
-------

All the following scripts are invoked by the $PHYSICS_TOP/mps_configuration/tool/mps_config.py script when creating new databases. For EIC the mps_gun_config.db has been copied to a versioned subdirectory (e.g. 2018-02-09-a) in the mps_configuration area.

Generate GUNB database - this creates the file mps_gun_config.db (sqlite file) that is used by other scripts to generate EPICS database and panels.

```
[mps_database]$ ./populate-gunb-t0.py
```

Export sqlite database (mps_gun_config.db) to YAML (mps_gun_config.yaml) file:

```
(venv)[lpiccoli@lcls-dev3 mps_database]$ ./export_yaml.py mps_gun_config.db mps_gun_config.yaml
Done.
```

Generate database documentation (Inputs/Faults):
```
[mps_database]$ ./export_docs.py mps_gun_config.db 
... (you may see many warnings) ...
```
The script generates documentation in pdf, rtf and html formats:
```
mps_database]$ ls -1 mps_gun_config.{rtf,pdf,html}
mps_gun_config.html
mps_gun_config.pdf
mps_gun_config.rtf
```
Export EPICS databases for central node IOC:
```
[mps_database]$ ./export_epics.py --device-inputs device_inputs.db --analog-devices analog_devices.db --mitigation-devices mitigation.db --faults faults.db --apps apps.db mps_gun_config.db
```
The command above generates file .db files:
- device_inputs.db for the digital inputs
- analog_devices.db for the analog inputs
- mitigation.db for the mitigation devices
- faults.db for the list of faults
- apps.db for the applications 

The source for the EPICS databases is the mps_gun_config.db file (sqlite format).

Export EDM panels for central node IOC:
```
[mps_database]$ ./export_edl.py mps_gun_config.db --device-inputs-edl device_inputs.edl --device-inputs-template templates/device_inputs.tmpl
```
Export EPICS databases for link node IOCs:
```
[mps_database]$ ./export_thresholds.py --app-id 2 --threshold-file threshold.template mps_gun_config.db

[mps_database]$ head -18 threshold.template
record(ao, "BPMS:GUNB:201:X_T0_HIHI") {
 field(DESC, "High analog threshold for X_T0")
 field(DTYP, "asynFloat64")
 field(OUT, "@asynMask(LINK_NODE 0 1 1)ANALOG_THRESHOLD")
}

record(ao, "BPMS:GUNB:201:X_T0_LOLO") {
 field(DESC, "Low analog threshold for X_T0")
 field(DTYP, "asynFloat64")
 field(OUT, "@asynMask(LINK_NODE 0 1 0)ANALOG_THRESHOLD")
}

record(ao, "BPMS:GUNB:201:X_T1_HIHI") {
 field(DESC, "High analog threshold for X_T1")
 field(DTYP, "asynFloat64")
 field(OUT, "@asynMask(LINK_NODE 0 2 1)ANALOG_THRESHOLD")
}
```
This creates the LOLO/HIHI analog output records for setting thresholds at the link node IOC. The thresolds are created per application card (--app-id parameter). The script also crates thresholds for the alternative, LCLS-I and idle modes. (LCLS-I and IDLE have a single HIHI/LOLO).

EIC History Server
------------------

```
mps_database]$ ./historyServer.py -h
usage: historyServer.py [-h] [--host hostname] [--port [port]] [--file [file]]
                        [--file-size [file_size]] [-c]
                        db

Receive MPS status messages

positional arguments:
  db                    database file name (e.g. mps_gun_config.db)

optional arguments:
  -h, --help            show this help message and exit
  --host hostname       Central node hostname
  --port [port]         server port (default=3356)
  --file [file]         History log file base, e.g. /data/history/mpshist -
                        file will be /data/history/mpshist-<DATE>.txt
  --file-size [file_size]
                        Maximum history log file size (default=10 MB)
  -c                    Print messages to stdout
```

Tests
-----

The 'central_node_test.py' script can be used to simulate firmware input data to the central node software. It sends update messages to the central node for each device state (e.g. valve on/valve off) and gets back a mitigation message, which is compared to the expected mitigation as described in the database.

The central node software must be compiled without the option '-DFW_ENABLE', which enables the software to receive updates and send mitigation to the test script instead of exchanging messages with the central node firmware (via CPSW). The central node software can run as a standalone server (see central_node_engine package under src/test/central_node_engine_server). The central node IOC may also be used for testing, but it must be linked against the non-FW_ENABLED central_node_engine lib.

Options for the script are:
```
mps_database]$ ./central_node_test.py -h
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
[mps_database]$ ./central_node_test.py mps_gun_config.db --host cpu-li00-mp01
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
[mps_database]$ ./central_node_test.py mps_gun_config.db --host cpu-li00-mp01 --device 1 --debug 1
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

Import CSV data
---------------

The script import/import-csv.py generates a database using csv exported files from the MPSInputList.xlsx (available from sharepoint). Currently it only populates some database tables, the devices/faults are not yet created. The generated database name is mps_config_imported.db.