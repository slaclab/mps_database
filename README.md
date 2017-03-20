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

Export EPICS databases for central node IOC:

$ python export_epics.py --device-inputs device_inputs.db mps_gun_config.db --analog-devices analog_devices.db --mitigation-devices mitigation.db --faults faults.db

The command above generates three .db files:
- device_inputs.db for the digital inputs
- analog_devices.db for the analog inputs
- mitigation.db for the mitigation devices
- faults.db for the list of faults

The source for the EPICS databases is the mps_gun_config.db file (sqlite format).