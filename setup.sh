
if [ $# == 1 ]; then
  if [ "$1" == "install" ]; then
    pip3 install virtualenv
    virtualenv venv
    source ./venv/bin/activate
    pip3 install -r requirements.txt
  elif [ "$1" == "prod" ]; then
    source $TOOLS/script/use_python3.bash
    export PYTHONPATH=${PWD}:${PWD}/tools:$PYTHONPATH
  fi
else
  source ./venv/bin/activate
  if [ $? == 1 ]; then
    echo "ERROR: use '. ./setup.sh install' command first"
    exit -1
  fi
  export PYTHONPATH=${PWD}:${PWD}/tools:$PYTHONPATH
fi

export LD_LIBRARY_PATH=$PACKAGE_TOP/python/python3.7.2/linux-x86_64/lib:$LD_LIBRARY_PATH
export PATH=$PACKAGE_TOP/python/python3.7.2/linux-x86_64/bin:$PATH
