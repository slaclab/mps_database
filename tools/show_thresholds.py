#!/usr/bin/env python
#
# Script for displaying current database thresholds for MPS analog devices
#

from mps_config import MPSConfig, models, runtime
from mps_names import MpsName
from runtime import *
from runtime_utils import RuntimeChecker
from sqlalchemy import func
import sys
import argparse
import time 
import os
import re
import subprocess
import yaml
import epics
from epics import PV
from argparse import RawTextHelpFormatter
from tabulate import tabulate

class ThresholdManager:
  """
  Changes thresholds of analog devices - save value in database and set device using channel access
  """
  def __init__(self, db, rt_db, verbose, print_all):
    self.mps = MPSConfig(args.database[0].name, args.database[0].name.split('.')[0]+'_runtime.db')
    self.session = self.mps.session
    self.rt_session = self.mps.runtime_session
    self.mps_names = MpsName(self.session)
    self.verbose = verbose
    self.print_all = print_all
    self.rt = RuntimeChecker(self.session, self.rt_session, self.verbose)
    
  def __exit__(self):
    self.session.close()
    self.rt_session.close()

  def get_thresholds(self, threshold_list, table):
    """
    table: '' => std
           'alt' => alt
           'lc1' => lc1
           'idl' => idl
    Returns:
    { 'i0h': { T0, T1, ..., T7 },
      'i0l': { T0, T1, ..., T7 },
      'i1h': { T0, T1, ..., T7 },
      'i1l': { T0, T1, ..., T7 },
      ...
    }
    """
    t = {}
#    for i in self.rt.integrators:

  def print_threshold_table(self, integrator, table, threshold_names, high_values, low_values):
    threshold_names.insert(0, integrator)
    high_values.insert(0, 'High')
    low_values.insert(0, 'Low')
    print('Threshold table: {}'.format(table))
    print(tabulate([threshold_names, high_values, low_values], tablefmt='grid'))
    print('')

  def print_thresholds(self, dev_id, dev_name):
    d = self.check_device(dev_id, dev_name)
    print('=== Database thresholds for device {} (id={}) ==='.\
            format(d.name, d.id))
    threshold_list = self.rt.get_thresholds(d)

    any_active = False
    for t in threshold_list:
      if (t['active']):
        any_active = True

    if (not any_active and not self.print_all):
      print('There are no thresholds defined for the device')
      return

    header = ['PV', 'Table', 'Integrator', 'Type', 'Value']
    table = []
    table.append(header)
    for t in threshold_list:
      row = []
      if (self.print_all or t['active']):
        row.append(t['pv'].pvname)
        row.append(t['db_table'])
        row.append(t['integrator'].upper())
        row.append(t['threshold_type'].upper())
        if (t['active']):
          row.append(t['value'])
        else:
          row.append('-')
        table.append(row)

    print(tabulate(table, tablefmt='grid'))

#    std_thresholds = get_thresholds(threshold_list, '')
#    for x in std_thresholds:
#      print x
#    print_threshold()


#    for t in threshold_list:
#      print t
#      print t['pv'].pvname
#      restore_item = {}
#      if (threshold_item['active']):
#        restore_item['device'] = rt_d
#        restore_item['pv'] = threshold_item['pv']
#        restore_item['value'] = threshold_item['value']
##        restore_list.append(restore_item)
#        if (self.verbose):
#          print('{}={}'.format(threshold_item['pv'].pvname, threshold_item['value']))

    return True

  def is_analog(self, dev_id):
    analog_devices = self.session.query(models.AnalogDevice).filter(models.AnalogDevice.id==dev_id).all()
    if (len(analog_devices)==1):
      return True
    else:
      digital_devices = self.session.query(models.DigitalDevice).filter(models.DigitalDevice.id==dev_id).all()
      if (len(digital_devices)==0):
        print 'ERROR: Device not found (invalid device id {0})'.format(dev_id)
      return False

  def check_device(self, dev_id, dev_name):
    if (dev_id < 0):
      try:
        d = self.session.query(models.Device).filter(models.Device.name==dev_name).one()
        dev_id = d.id
      except:
        print 'ERROR: Cannot find device "{0}"'.format(dev_name)
        return False

    if (self.is_analog(dev_id)):
      try:
        rt_d = self.rt_session.query(runtime.Device).filter(runtime.Device.id==dev_id).one()
        d = self.session.query(models.Device).filter(models.Device.id==dev_id).one()
      except:
        print 'ERROR: Cannot find device "{0}"'.format(dev_id)
        return False

      if (rt_d.mpsdb_name != d.name):
        print 'ERROR: Device names do not match in config ({0}) and runtime databases ({1})'.\
            format(d.name, rt_d.mpsdb_name)
        return False

      self.is_bpm = False
      if (d.device_type.name == 'BPMS'):
        self.is_bpm = True

    else:
      print 'ERROR: Cannot set threshold for digital device'
      return False

    return d
    
#=== MAIN ==================================================================================

parser = argparse.ArgumentParser(description='Change thresholds for analog devices',
                                 formatter_class=RawTextHelpFormatter)
parser.add_argument('database', metavar='db', type=file, nargs=1, 
                    help='database file name (e.g. mps_gun.db, where the runtime database is named mps_gun_runtime.db')

parser.add_argument('-v', action='store_true', default=False,
                    dest='verbose', help='verbose output')
parser.add_argument('-a', action='store_true', default=False,
                    dest='print_all', help='print all thresholds, even those not yet defined')
group_list = parser.add_mutually_exclusive_group()
group_list.add_argument('--device-id', metavar='database device id', type=int, nargs='?', help='database id for the device')
group_list.add_argument('--device-name', metavar='database device name (e.g. BPM1B)', type=str, nargs='?', help='device name as found in the MPS database')

args = parser.parse_args()

device_id = -1
if (args.device_id):
  device_id = args.device_id

device_name = None
if (args.device_name):
  device_name =args.device_name

tm = ThresholdManager(args.database[0].name,
                      args.database[0].name.split('.')[0]+'_runtime.db',
                      args.verbose, args.print_all)

tm.print_thresholds(device_id, device_name)
