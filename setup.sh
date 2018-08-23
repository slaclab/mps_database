
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
  fi
fi

#export LD_LIBRARY_PATH=$PACKAGE_TOP/python/python2.7.9/linux-x86_64/lib:$LD_LIBRARY_PATH
#export PATH=$PACKAGE_TOP/python/python2.7.9/linux-x86_64/bin:$PATH
