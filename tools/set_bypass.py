#!/usr/bin/env python

from mps_config import MPSConfig, models, runtime
from mps_names import MpsName
from runtime import *
from sqlalchemy import func
import subprocess
import argparse
import time 
import sys
import os
import re
from argparse import RawTextHelpFormatter

def isAnalog(session, dev_id):
  analog_devices = session.query(models.AnalogDevice).filter(models.AnalogDevice.id==dev_id).all()
  if (len(analog_devices)==1):
    return True
  else:
    digital_devices = session.query(models.DigitalDevice).filter(models.DigitalDevice.id==dev_id).all()
    if (len(digital_devices)==0):
      print 'ERROR: Device not found (invalid device id {0})'.format(dev_id)
    return False

def addHistory(rt_session, table_k, t_index, rt_d, t_table, user, reason):
  hist_name = getThresholdHistoryName(table_k, t_index)
  hist_class = globals()[hist_name]
  hist = hist_class(user=user, reason=reason, device_id=rt_d.id)

  # Copy thresholds from rt_d.threshold to history
  for k in getattr(rt_d, t_table).__dict__.keys():
    if (re.match('i[0-3]_[lh]', k)):
      db_value = float(getattr(getattr(rt_d, t_table), k))
#      print '{0} {1}'.format(k, db_value)
      setattr(hist, k, db_value)
      
  rt_session.add(hist)
  rt_session.commit()

  return True

#
# Update the thresholds in database and make enty in the history table.
#
def changeThresholds(session, rt_session, rt_d, table, user, reason):
  log = '=== Threshold Change for device "{0}" ===\n'.format(rt_d.mpsdb_name)
  log = log + 'User: {0}\n'.format(user)
  log = log + 'Reason: {0}\n'.format(reason)
  log = log + 'Date: {0}\n\n'.format(time.strftime("%Y/%m/%d %H:%M:%S"))

  for table_k, table_v in table.items():
    for threshold_k, threshold_v in table_v.items():
      for integrator_k, integrator_v in threshold_v.items():
        # Get threshold table
        t_table = getThresholdTableName(table_k, integrator_k, threshold_k)
        for value_k, value_v in integrator_v.items():
          old_value = getattr(getattr(rt_d, t_table), '{1}_{2}'.format(t_table, integrator_k, value_k))
          log = log + 'threshold={0} integrator={1} type={2} prev={3} new={4}\n'.format(threshold_k, integrator_k, value_k, old_value, value_v)
          updateThreshold(rt_session, rt_d, t_table, integrator_k, value_k, value_v)

      addHistory(rt_session, table_k, threshold_k, rt_d, t_table, user, reason)

  log = log + "===\n"
  print log
  return True


def addDeviceInputBypassHistory(session, rt_session, rt_di, user, reason, startdate, duration):
  bypass_hist = runtime.BypassHistory(startdate=startdate, duration=duration,
                                      value=0, user=user, reason=reason, device_input_id=rt_di.id)
  rt_session.add(bypass_hist)
  rt_session.commit()
  
  return True

def addAnalogBypassHistory(session, rt_session, rt_d, user, reason, startdate, duration):
  bypass_hist = runtime.BypassHistory(startdate=startdate, duration=duration,
                                      value=0, user=user, reason=reason, device_id=rt_d.id)
  rt_session.add(bypass_hist)
  rt_session.commit()
  
  return True

#
#
#
def setBypass(session, rt_session, bypass, time_now, user, reason, duration):
  # Bypass would expire at
  new_expiration = time_now + duration

  # Set bypass if new expiration date is greater than existing
  prev_expiration = bypass.startdate + bypass.duration
  if (duration == 0):
    bypass.duration = 0
    rt_session.commit()
  elif (new_expiration != prev_expiration):
    if (bypass.duration == 0 or 
        (bypass.duration > 0 and prev_expiration < time_now)):
      print ('INFO: New bypass set to expire at {0}'.\
               format(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(new_expiration))))
    elif (new_expiration < prev_expiration):
      print ('INFO: Setting bypass to expire earlier (previous date: {0}, new date: {1}'.\
               format(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(prev_expiration)),
                      time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(new_expiration))))
    else:
      print ('INFO: Setting bypass to expire later (previous date: {0}, new date: {1}'.\
               format(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(prev_expiration)),
                      time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(new_expiration))))
    bypass.startdate = time_now
    bypass.duration = duration
    rt_session.commit()
  else:
    print 'WARN: Specified bypass expiration date is the same as before'
    return False

  return True

#
# Set bypass for device input
#
def setDeviceInputBypass(session, rt_session, rt_di, user, reason, duration):
  # This is the current time
  time_now = int(time.time())

  if (setBypass(session, rt_session, rt_di.bypass, time_now, user, reason, duration)):
    addDeviceInputBypassHistory(session, rt_session, rt_di, user, reason, time_now, duration)
    return True
  else:
    return False

#
# Set bypass for an analog device
#
# Check if there is an active bypass - i.e. if the bypass.duration database
# entry is populated, then check if the new duration goes beyond. If that is 
# the case then extend the bypass. If duration is lesser or equal than the
# current one don't update.
#
# If the specified duration is zero, then if there is an active bypass it \
# should be cancelled.
#
def setAnalogBypass(session, rt_session, rt_d, user, reason, duration):
  # This is the current time
  time_now = int(time.time())

  if (setBypass(session, rt_session, rt_d.bypass, time_now, user, reason, duration)):
    addAnalogBypassHistory(session, rt_session, rt_d, user, reason, time_now, duration)
    return True
  else:
    return False
               
def checkDeviceInput(session, rt_session, device_input_id, device_input_pv):
  rt_di = None
  rt_di_id = -1
  if (device_input_id < 0):
    try:
      rt_di = rt_session.query(runtime.DeviceInput).filter(runtime.DeviceInput.pv_name==device_input_pv).one()
      rt_di_id = rt_di.id
    except:
      print 'ERROR: Cannot find device input with the PV name "{0}" in runtime database'.\
          format(device_input_pv)
      return False
  else:
    try:
      rt_di = rt_session.query(runtime.DeviceInput).filter(runtime.DeviceInput.mpsdb_id == device_input_id).one()
    except:
      print 'ERROR: Cannot find device input with id={0} in runtime database'.\
          format(device_input_id)
      return False

  # 
  # Make sure the databases are in sync, i.e. ids are consistent
  #
  if (rt_di == None):
    return False
  else:
    # 1) Find the device_inputs from MPS database (from the id stored in the runtime DB)
    try:
      di = session.query(models.DeviceInput).filter(models.DeviceInput.id == rt_di.mpsdb_id).one()
    except:
      print 'ERROR: Failed to find device input in MPS database (it exists in runtime). Please check databases, there are inconsistencies!'.\
          format()
      return False

    # 2) Find the device in the MPS database associated with the device_input
    try:
      d = session.query(models.Device).filter(models.Device.id == di.digital_device_id).one()
    except:
      print 'ERROR: Failed to find digital device associated with digital input in MPS database, please check database'
      return False

    # 3) Find the same device, but now in the runtime DB. 
    try:
      rt_d = rt_session.query(runtime.Device).filter(runtime.Device.mpsdb_id == di.digital_device_id).one()
    except:
      print 'ERROR: Failed to find digital device associated with digital input in runtime database, please check database'

    # 4) Device names must be the same
    if d.name != rt_d.mpsdb_name:
      print 'ERROR: Device names do not match in config ({0}) and runtime databases ({1})'.\
          format(d.name, rt_d.mpsdb_name)
      return False

  return rt_di

def checkAnalogDevice(session, rt_session, dev_id, dev_name):
  if (dev_id < 0):
    try:
      d = session.query(models.Device).filter(models.Device.name==dev_name).one()
      dev_id = d.id
    except:
      print 'ERROR: Cannot find device "{0}"'.format(dev_name)
      return False

  if (isAnalog(session, dev_id)):
    try:
      rt_d = rt_session.query(runtime.Device).filter(runtime.Device.id==dev_id).one()
      d = session.query(models.Device).filter(models.Device.id==dev_id).one()
    except:
      print 'ERROR: Cannot find device "{0}"'.format(dev_id)
      return False

  else:
    print 'ERROR: Cannot set bypass for digital device, must specify device input information'
    return False

  print rt_d.mpsdb_name
  return rt_d

#=== MAIN ==================================================================================

parser = argparse.ArgumentParser(description='Set bypass for analog device or device input (digital)',
                                 formatter_class=RawTextHelpFormatter)
parser.add_argument('database', metavar='db', type=file, nargs=1, 
                    help='database file name (e.g. mps_gun.db)')
parser.add_argument('--reason', metavar='Reason for the bypass setting', type=str, nargs=1,
                    help='reason for the threshold change', required=True)
parser.add_argument('--time', metavar='seconds', type=int, nargs=1,
                    help='Bypass duration is seconds, starting from now.\n' +
                    'Use zero seconds to cancel bypass', required=True)

group_list = parser.add_mutually_exclusive_group()
group_list_analog = group_list.add_mutually_exclusive_group()
group_list_analog.add_argument('--analog-device-id', metavar='database analog device id', type=int, nargs='?',
                               help='Database id for the device - must be analog device')
group_list_analog.add_argument('--analog-device-name', metavar='database device name', 
                               type=str, nargs='?', help='Analog device name as found in the MPS database (e.g. BPM1B)')
group_list_digital = group_list.add_mutually_exclusive_group()
group_list_digital.add_argument('--device-input-id', metavar='database device input id', type=int, nargs='?',
                                help='Database id for the device input - use for digital devices')
group_list_digital.add_argument('--device-input-pv', metavar='pv name of device input', 
                               type=str, nargs='?', help='Device input PV (e.g. PROF:GUNB:753:IN_SWITCH)')

proc = subprocess.Popen('whoami', stdout=subprocess.PIPE)
user = proc.stdout.readline().rstrip()

args = parser.parse_args()

device_input_id = -1
if (args.device_input_id):
  device_input_id = args.device_input_id

device_input_pv = None
if (args.device_input_pv):
  device_input_pv = args.device_input_pv

device_id = -1
if (args.analog_device_id):
  device_id = args.analog_device_id

device_name = None
if (args.analog_device_name):
  device_name =args.analog_device_name

reason = args.reason[0]
duration = int(args.time[0])
mps = MPSConfig(args.database[0].name, args.database[0].name.split('.')[0]+'_runtime.db')
session = mps.session
rt_session = mps.runtime_session

rt_d = None
if (device_id != -1 or device_name != None):
  rt_d = checkAnalogDevice(session, rt_session, device_id, device_name)
else:
  rt_di = checkDeviceInput(session, rt_session, device_input_id, device_input_pv)

if (rt_d):
  setAnalogBypass(session, rt_session, rt_d, user, reason, duration) 
elif (rt_di):
  setDeviceInputBypass(session, rt_session, rt_di, user, reason, duration)
#  table = buildThresholdTable(rt_d, args.t)
#  if (table):
#    if (verifyThresholds(session, rt_session, rt_d, table)):
#      if (not changeThresholds(session, rt_session, rt_d, table, user, reason)):
#        session.close()
#        rt_session.close()
#        exit(-1)

session.close()
rt_session.close()
