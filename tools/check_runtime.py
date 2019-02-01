#!/usr/bin/env python

from mps_config import MPSConfig, models, runtime
from mps_names import MpsName
from sqlalchemy import func
import sys
import argparse
import time 
import os

def check(session, rt_session):
  mpsName = MpsName(session)

  # First check the devices in both databases
  devices = session.query(models.Device).all()
  rt_devices = rt_session.query(runtime.Device).all()
  
  if (len(devices) != len(rt_devices)):
    print 'ERROR: Number of devices in databases must be the same'
    print '       found {0} devices in config database'.format(len(devices))
    print '       found {0} devices in runtime database'.format(len(rt_devices))
    return False

  # Extract device_ids and names and sort
  d = [ [i.id, i.name] for i in devices ]
  d.sort()

  rt_d = [ [i.mpsdb_id, i.mpsdb_name] for i in rt_devices ]
  rt_d.sort()

  # Compare one by one the devices, they must be exactly the same
  for a, b in zip(d, rt_d):
    if (a[0] != b[0] or a[1] != b[1]):
      print 'ERROR: Mismatched devices found'
      print '       {0} [id={1}] in config database'.format(a[0], a[1])
      print '       {0} [id={1}] in runtime database'.format(b[0], b[1])
      return False

  # Now check the device_inputs (i.e. digital devices)
  device_inputs = session.query(models.DeviceInput).all()
  rt_device_inputs = rt_session.query(runtime.DeviceInput).all()

  # Extract device_ids and names and sort
  di = [ [i.id, mpsName.getDeviceInputName(i)] for i in device_inputs ]
  d.sort()

  rt_di = [ [i.mpsdb_id, i.pv_name] for i in rt_device_inputs ]
  rt_di.sort()

  # Compare one by one the device inputs, they must be exactly the same
  for a, b in zip(di, rt_di):
    if (a[0] != b[0] or a[1] != b[1]):
      print 'ERROR: Mismatched devices found'
      print '       {0} [id={1}] in config database'.format(a[0], a[1])
      print '       {0} [id={1}] in runtime database'.format(b[0], b[1])
      return False

#=== MAIN ==================================================================================

parser = argparse.ArgumentParser(description='Check consistency between MPS configuration and runtime databases')
parser.add_argument('database', metavar='db', type=file, nargs=1, 
                    help='database file name (e.g. mps_gun.db)')
parser.add_argument('rt_database', metavar='runtime_db', type=file, nargs=1, 
                    help='runtime database file name (e.g. mps_gun_runtime.db)')

args = parser.parse_args()

mps = MPSConfig(args.database[0].name, args.rt_database[0].name)
session = mps.session
rt_session = mps.runtime_session

check(session, rt_session)

session.close()
rt_session.close()
