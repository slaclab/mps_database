export LD_LIBRARY_PATH=$PACKAGE_TOP/python2.7.9/linux-x86_64/lib:$LD_LIBRARY_PATH
export PATH=$PACKAGE_TOP/python2.7.9/linux-x86_64/bin:$PATH

if [ $# == 1 ]; then
  if [ "$1" == "install" ]; then
    pip install virtualenv
    virtualenv venv
    source ./venv/bin/activate
    pip install -r requirements.txt
  fi
else
  source ./venv/bin/activate
  if [ $? == 1 ]; then
    echo "ERROR: use '. ./setup.sh install' command first"
  fi
fi
