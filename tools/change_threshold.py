#!/usr/bin/env python

from mps_config import MPSConfig, models, runtime
from mps_names import MpsName
from runtime import *
from sqlalchemy import func
import sys
import argparse
import time 
import os
import re
import subprocess
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

#
# Save threshold to the database as current value
#
def updateThreshold(rt_session, rt_d, t_table, integrator_k, t_type, value_v):
  setattr(getattr(rt_d, t_table), '{0}_{1}'.format(integrator_k,t_type), value_v)
  rt_session.commit()

def getThresholdHistoryName(table_k, t_index):
  if (table_k == 'idl'):
    return 'ThresholdHistoryIdl'
  elif (table_k == 'lc1'):
    return 'ThresholdHistoryLc1'
  elif (table_k == 'lc2'):
    return 'Threshold{0}History'.format(t_index[1])
  elif (table_k == 'alt'):
    return 'ThresholdAlt{0}History'.format(t_index[1])

  return None
  
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

def checkDevice(session, rt_session, dev_id, dev_name):
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

    if (rt_d.mpsdb_name != d.name):
      print 'ERROR: Device names do not match in config ({0}) and runtime databases ({1})'.\
          format(d.name, rt_d.mpsdb_name)
      return False

  else:
    print 'ERROR: Cannot set threshold for digital device'
    return False

  return rt_d

def getThresholdTableName(table_name, integrator_name, threshold_name):
  if (table_name == 'lc2'):
    t_table = 'threshold{0}'.format(threshold_name[1])

  if (table_name == 'alt'):
    t_table = 'threshold_alt{0}'.format(threshold_name[1])

  if (table_name == 'lc1'):
    t_table = 'threshold_lc1'

  if (table_name == 'idl'):
    t_table = 'threshold_idl'

  return t_table

#
# Check if the specified thresholds are valid, i.e. HIHI > LOLO value
# If only the LOLO or HIHI is specified, then check against the
# current value in the database
#
def verifyThresholds(session, rt_session, rt_d, table):

  for table_k, table_v in table.items():
    for threshold_k, threshold_v in table_v.items():
      for integrator_k, integrator_v in threshold_v.items():

        new_low = None
        new_high = None

        if ('l' in integrator_v.keys()):
          new_low = float(integrator_v['l'])
        if ('h' in integrator_v.keys()):
          new_high = float(integrator_v['h'])


        if (new_low != None and new_high != None):
          if (new_low >= new_high):
            print 'ERROR: Invalid thresholds for device {0}, table {1}, integrator {2}, threshold {3}'.\
                format(rt_d.mpsdb_name, table_k, integrator_k, threshold_k)
            print 'ERROR: HIHI threshold (value={0}) smaller or equal to LOLO (value={1}), cannot proceed'.format(new_high, new_low)
            return False

        if (new_low == None or new_high == None):
          t_table = getThresholdTableName(table_k, integrator_k, threshold_k)
          t_type = 'h'
          if (new_low == None):
            t_type = 'l'
          
          db_value = float(getattr(getattr(rt_d, t_table), '{0}_{1}'.format(integrator_k,t_type)))
          
          if (new_low == None):
#            print 'Checking new_high{1} <= db_value{0}'.format(db_value, new_high)
            if (new_high <= db_value):
              print 'ERROR: Invalid thresholds for device {0}, table {1}, integrator {2}, threshold {3}'.\
                format(rt_d.mpsdb_name, table_k, integrator_k, threshold_k)
              print 'ERROR: Specified HIHI value ({0}) is smaller or equal than the database LOLO value ({1})'.\
                  format(new_high, db_value)
              return False

          if (new_high == None):
 #           print 'Checking new_low {0} >= db_value{1}'.format(new_low, db_value)
            if (new_low >= db_value):
              print 'ERROR: Invalid thresholds for device {0}, table {1}, integrator {2}, threshold {3}'.\
                format(rt_d.mpsdb_name, table_k, integrator_k, threshold_k)
              print 'ERROR: Specified LOLO value ({0}) is greater or equal than the database HIHI value ({1})'.\
                  format(new_low, db_value)
              return False
          
#        print 'low={0} high={1}'.format(new_low, new_high)

  return True

#
# Build a table/dictionary from the command line parameters
#
def buildThresholdTable(rt_d, t):
  # fist check the parameters
  for l in t:
    [table_name, t_index, integrator, t_type, value] = l

    table_name = table_name.lower()
    t_index = t_index.lower()
    integrator = integrator.lower()
    t_type = t_type.lower()

    if (table_name != 'lc2' and
        table_name != 'alt' and
        table_name != 'lc1' and
        table_name != 'idl'):
      print 'ERROR: Invalid thresholds for device {0}, table {1}, integrator {2}, threshold {3}'.\
          format(rt_d.mpsdb_name, table_name, integrator, t_index)
      print 'ERROR: Invalid table "{0}" (parameter={1})'.format(l[0], l)
      return False

    if (not (((integrator.startswith('i')) and
              len(integrator)==2 and
              int(integrator[1])>=0 and
              int(integrator[1])<=3) or
             integrator=='x' or
             integrator=='y' or
             integrator=='tmit')):
      print 'ERROR: Invalid thresholds for device {0}, table {1}, integrator {2}, threshold {3}'.\
          format(rt_d.mpsdb_name, table_name, integrator, t_index)
      print 'ERROR: Invalid integrator "{0}" (parameter={1})'.format(integrator, l)
      return False
      
    if (not (t_index.startswith('t'))):
      print 'ERROR: Invalid thresholds for device {0}, table {1}, integrator {2}, threshold {3}'.\
          format(rt_d.mpsdb_name, table_name, integrator, t_index)
      print 'ERROR: Invalid threshold "{0}", must start with T (parameter={1})'.format(t_index, l)
      return False
    else:
      if (len(t_index) != 2):
        print 'ERROR: Invalid thresholds for device {0}, table {1}, integrator {2}, threshold {3}'.\
            format(rt_d.mpsdb_name, table_name, integrator, t_index)
        print 'ERROR: Invalid threshold "{0}", must be in T<index> format (parameter={1})'.format(t_index, l)
        return False
      else:
        if (table_name == 'lc2' or table_name == 'alt'):
          if (int(t_index[1])<0 or int(t_index[1])>7):
            print 'ERROR: Invalid thresholds for device {0}, table {1}, integrator {2}, threshold {3}'.\
                format(rt_d.mpsdb_name, table_name, integrator, t_index)
            print 'ERROR: Invalid threshold index "{0}", must be between 0 and 7 (parameter={1})'.\
                format(t_index[1], l)
            return False
        else:
          if (int(t_index[1]) != 0):
            print 'ERROR: Invalid thresholds for device {0}, table {1}, integrator {2}, threshold {3}'.\
                format(rt_d.mpsdb_name, table_name, integrator, t_index)
            print 'ERROR: Invalid threshold index "{0}", must be 0'.\
                format(t_index[1], l)
            return False

    if (not (t_type == 'lolo' or
             t_type == 'hihi')):
      print 'ERROR: Invalid thresholds for device {0}, table {1}, integrator {2}, threshold {3}'.\
          format(rt_d.mpsdb_name, table_name, integrator, t_index)
      print 'ERROR: Invalid threshold type "{0}", must be LOLO or HIHI (parameter={1})'.\
          format(t_type, l)
      return False

  # build a dictionary with the input parameters
  table = {}
  for l in t:
    [table_name, t_index, integrator, t_type, value] = l

    table_name = table_name.lower()
    t_index = t_index.lower()
    integrator = integrator.lower()
    t_type = t_type.lower()

    # Rename fields to match database
    if (integrator == 'x'):
      integrator = 'i0'

    if (integrator == 'y'):
      integrator = 'i1'

    if (integrator == 'tmit'):
      integrator = 'i2'

    if (t_type == 'lolo'):
      t_type = 'l'

    if (t_type == 'hihi'):
      t_type = 'h'

    if (not table_name in table.keys()):
      table[table_name]={}

    if (not t_index in table[table_name].keys()):
      table[table_name][t_index]={}

    if (not integrator in table[table_name][t_index].keys()):
      table[table_name][t_index][integrator]={}

    if (not t_type in table[table_name][t_index][integrator].keys()):
      table[table_name][t_index][integrator][t_type]=value

  return table
    
#=== MAIN ==================================================================================

parser = argparse.ArgumentParser(description='Change analog device threshold of a device',
                                 formatter_class=RawTextHelpFormatter)
parser.add_argument('database', metavar='db', type=file, nargs=1, 
                    help='database file name (e.g. mps_gun.db)')
parser.add_argument('--reason', metavar='reason', type=str, nargs=1, help='reason for the threshold change', required=True)
parser.add_argument('-t', nargs=5, action='append', 
                    help='<table threshold_index integrator threshold_type value>\nwhere:\n'+
                         '  table: lc2, alt, lc1 or idl\n'
                         '  threshold_index: T0 through T7 (must be T0 for LCLS-I and IDLE thresholds)\n'+
                         '  integrator_index: I0, I1, I2, I3, X, Y or TMIT\n'+
                         '  threshold_type: LOLO or HIHI\n'+
                         '  value: new threshold value\n\nTables:\n'+
                         '  lc2: LCLS-II thresholds\n'+
                         '  alt: alternative LCLS-II thresholds\n'+
                         '  lc1: LCLS-I thresholds, only T0 available\n'+
                         '  idl: no beam thresholds, only T0 available\n')

group_list = parser.add_mutually_exclusive_group()
group_list.add_argument('--device-id', metavar='database device id', type=int, nargs='?', help='database id for the device')
group_list.add_argument('--device-name', metavar='database device name (e.g. BPM1B)', type=str, nargs='?', help='device name as found in the MPS database')

proc = subprocess.Popen('whoami', stdout=subprocess.PIPE)
user = proc.stdout.readline().rstrip()

args = parser.parse_args()

device_id = -1
if (args.device_id):
  device_id = args.device_id

device_name = None
if (args.device_name):
  device_name =args.device_name

reason = args.reason[0]

mps = MPSConfig(args.database[0].name, args.database[0].name.split('.')[0]+'_runtime.db')
session = mps.session
rt_session = mps.runtime_session

rt_d = checkDevice(session, rt_session, device_id, device_name)
if (rt_d):
  table = buildThresholdTable(rt_d, args.t)
  if (table):
    if (verifyThresholds(session, rt_session, rt_d, table)):
      if (not changeThresholds(session, rt_session, rt_d, table, user, reason)):
        session.close()
        rt_session.close()
        exit(-1)

#changeThresholds(session, rt_session, device_id)
session.close()
rt_session.close()
