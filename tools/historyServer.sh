#!/bin/bash

if [ $# != '1' ]; then
  echo 'Usage: '$0' start/stop'
  exit 1
fi

if [ $1 == 'start' ]; then
  echo 'Starting...'

  export PYTHONPATH=$PHYSICS_TOP/mps_database:$PYTHON_PATH

  current_db=$PHYSICS_TOP/mps_configuration/current
  history_files=$PHYSICS_DATA/mps_history/mps_history
  files=`ls $current_db/mps_config*.db | wc -l`

  if [ $files != '1' ]; then
    echo 'ERROR: found '$files' database files in '$current_db
    echo '       there must be only one mps_config-<release>.db file'
    echo '       historyServer is confused and cannot run.'
  fi

  db_file=`ls $current_db/mps_config*.db`

  if [ `hostname` == 'lcls-dev3' ]; then
    history_files=/tmp/mps_history
  fi

  $PHYSICS_TOP/mps_database/tools/historyServer.py --port 3356 $db_file --file $history_files --file-size `echo '1024*1024*10'|bc -l` &

elif [ $1 == 'stop' ]; then
  echo 'Stopping...'
fi
