
if [ $# == 1 ]; then
  if [ "$1" == "install" ]; then
    pip install virtualenv
    virtualenv venv
    source ./venv/bin/activate
    pip install -r requirements.txt
  elif [ "$1" == "prod" ]; then
    source $TOOLS/script/go_python2.7.13.bash
    export PYTHONPATH=$PHYSICS_TOP/mps_database:$PYTHONPATH
  fi
else
  source ./venv/bin/activate
  if [ $? == 1 ]; then
    echo "ERROR: use '. ./setup.sh install' command first"
    exit -1
  fi
  export PYTHONPATH=/u/ld/jmock/Cosylab/workspace/mps_database/mps_database-cu-turn-on:$PYTHONPATH
fi

export LD_LIBRARY_PATH=$PACKAGE_TOP/python/python2.7.9/linux-x86_64/lib:$LD_LIBRARY_PATH
export PATH=$PACKAGE_TOP/python/python2.7.9/linux-x86_64/bin:$PATH
