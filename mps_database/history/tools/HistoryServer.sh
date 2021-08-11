#!/bin/bash
#This file has been copied & lightly edited from the depreciated EicHistoryServer.
echo 'Starting...'

#TODO: get the right python version/configurations 
. $TOOLS/script/go_python2.7.13.bash
export PYTHONPATH=$PHYSICS_TOP/mps_database:$PYTHON_PATH

current_db=$PHYSICS_TOP/mps_configuration/current
history_files=$PHYSICS_DATA/mps_history/mps_history
files=`ls $current_db/mps_config*.db | grep -v runtime |  wc -l`

#TODO: do own error checking for history db, this isn't accurate
#if [ $files != '1' ]; then
#  echo 'ERROR: found '$files' database files in '$current_db
#  echo '       there must be only one mps_config-<release>.db file'
#  echo '       historyServer is confused and cannot run.'
#fi

#TODO: set database location for new history server
#db_file=`ls $current_db/mps_config*.db | grep -v runtime`

#TODO: lcls-dev3 has another location, same as other shit
if [ `hostname` == 'lcls-dev3' ]; then
  history_files=/tmp/mps_history
fi
#TODO:this might be the same?
$PHYSICS_TOP/mps_database/tools/EicHistoryServer.py --port 3356 $db_file --file $history_files --file-size `echo '1024*1024*10'|bc -l` &
