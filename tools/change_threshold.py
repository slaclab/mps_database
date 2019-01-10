#!/usr/bin/env python

from mps_config import MPSConfig, models, runtime
from mps_names import MpsName
from sqlalchemy import func
import sys
import argparse
import time 
import os

def isAnalog(session, dev_id):
  analog_devices = session.query(models.AnalogDevice).filter(models.AnalogDevice.id==dev_id).all()
  if (len(analog_devices)==1):
    return True
  else:
    return False

def addHistoryIdl(rt_session, device, user, reason):
  hist = runtime.ThresholdHistoryIdl(l=device.threshold_idl.l, h=device.threshold_idl.h, user=user, reason=reason, device_id=device.id)
  rt_session.add(hist)
  rt_session.commit()

def doChangeThresholdIdl(rt_session, device, user, reason, new_high):
  print 'hi'
  device.threshold_idl.h = new_high
  rt_session.commit()
  addHistoryIdl(rt_session, device, user, reason)

def addHistoryLc1(rt_session, device, user, reason):
  hist = runtime.ThresholdHistoryLc1(l=device.threshold_idl.l, h=device.threshold_idl.h, user=user, reason=reason, device_id=device.id)
  rt_session.add(hist)
  rt_session.commit()

def doChangeThresholdLc1(rt_session, device, user, reason, new_high):
  print 'hi'
  device.threshold_lc1.h = new_high
  rt_session.commit()
  addHistoryLc1(rt_session, device, user, reason)

def changeThreshold(session, rt_session):
  dev_id = 10
  user = 'lpiccoli'
  reason = 'database test'
  new_high = 3.141567

  if (isAnalog(session, dev_id)):
    try:
      rt_d = rt_session.query(runtime.Device).filter(runtime.Device.id==dev_id).one()
      d = session.query(models.Device).filter(models.Device.id==dev_id).one()
    except:
      print 'ERROR: Cannot find device {0}'.format(dev_id)
      return False

    if (rt_d.mpsdb_name != d.name):
      print 'ERROR: Device names do not match in config ({0}) and runtime databases ({1})'.\
          format(d.name, rt_d.mpsdb_name)
      return False

    doChangeThresholdIdl(rt_session, rt_d, user, reason, new_high)
    doChangeThresholdLc1(rt_session, rt_d, user, reason, new_high)

  else:
    print 'ERROR: Cannot set threshold for digital device'
    return False

  return True

#=== MAIN ==================================================================================

parser = argparse.ArgumentParser(description='Change analog device threshold')
parser.add_argument('database', metavar='db', type=file, nargs=1, 
                    help='database file name (e.g. mps_gun.db)')

args = parser.parse_args()

mps = MPSConfig(args.database[0].name, args.database[0].name.split('.')[0]+'_runtime.db')
session = mps.session
rt_session = mps.runtime_session

changeThreshold(session, rt_session)

session.close()
rt_session.close()
