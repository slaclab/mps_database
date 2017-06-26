LCLS-II MPS Database 

This package contains SQLAlchemy python classes that provide access to the
MPS sqlite3 database. The classes are listed under the models subdirectory

Instructions
------------

On lcls-dev3, after cloning the repo (git clone git@github.com:slaclab/mps_database.git)
you need to use a python that has sqlite support:

> export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/afs/slac/g/lcls/package/python/python2.7.9/linux-x86_64/lib
> export PATH=$PACKAGE_TOP/python/python2.7.9/linux-x86_64/bin/:$PATH

You probably want to make a virtual environment for this project, to keep its module
dependencies separate from your global python install.  If you don’t already have
virtualenv (it is already installed in lcls-dev3) run:
> pip install virtualenv

Now, go into the mps_database directory and run:
> virtualenv venv

After it finishes, activate the virtual environment:
> source ./venv/bin/activate

Next, install all the modules the project uses:
> pip install -r requirements.txt

Scripts
-------

Generate GUNB database - this creates the file mps_gun_config.db (sqlite file) that is used by other scripts to generate EPICS database and panels.

> mps_database$ ./populate-gunb.py

Export sqlite database (mps_gun_config.db) to YAML (mps_gun_config.yaml) file:

(venv)[lpiccoli@lcls-dev3 mps_database]$ python
Python 2.7.9 (default, Apr 28 2015, 19:45:00)
[GCC 4.4.7 20120313 (Red Hat 4.4.7-11)] on linux2
Type "help", "copyright", "credits" or "license" for more information.
>>> import ioc_tools
>>> from mps_config import models, MPSConfig
>>> mps=MPSConfig("mps_gun_config.db")
>>> ioc_tools.dump_db_to_yaml(mps, "mps_gun_config.yaml")

Print database contents (Faults/Logic):

> mps_database$ ./printdb mps_gun_config.db

Export EPICS databases for central node IOC:

> $ ./export_epics.py --device-inputs device_inputs.db mps_gun_config.db --analog-devices analog_devices.db --mitigation-devices mitigation.db --faults faults.db

The command above generates three .db files:
- device_inputs.db for the digital inputs
- analog_devices.db for the analog inputs
- mitigation.db for the mitigation devices
- faults.db for the list of faults

The source for the EPICS databases is the mps_gun_config.db file (sqlite format).

Export EDM panels for central node IOC:

> $ ./export_edl.py mps_gun_config.db --device-inputs-edl device_inputs.edl --device-inputs-template templates/device_inputs.tmpl

