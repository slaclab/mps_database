#!/usr/bin/env python
#
# Script for restoring thresholds for MPS analog devices. Thresholds for analog devices
# for the specified global app id will be restored using values in the runtime database
#
# Exit codes:
# 1 - Failed to restore one or more PVs
# 2 - Failed to check on or more PVs
#

from mps_config import MPSConfig, models, runtime
from mps_names import MpsName
from runtime_utils import RuntimeChecker
from runtime import *
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

class ThresholdRestorer:
  threshold_tables = ['threshold0','threshold1','threshold2','threshold3',
                      'threshold4','threshold5','threshold6','threshold7',
                      'threshold_alt0', 'threshold_alt1','threshold_alt2', 'threshold_alt3',
                      'threshold_alt4', 'threshold_alt5','threshold_alt6', 'threshold_alt7',
                      'threshold_lc1', 'threshold_idl']
  threshold_tables_pv = ['lc2', 'lc2', 'lc2', 'lc2', 'lc2', 'lc2', 'lc2', 'lc2',
                         'alt', 'alt', 'alt', 'alt', 'alt', 'alt', 'alt', 'alt', 
                         'lc1', 'idl']
  threshold_types = ['l','h']
  integrators = ['i0','i1','i2','i3']
  threshold_index = ['t0', 't1', 't2', 't3', 't4', 't5', 't6', 't7',
                     't0', 't1', 't2', 't3', 't4', 't5', 't6', 't7',
                     't0', 't0']
  """
  Restory thresholds of analog devices - using latest thresholds saved in database
  """
  def __init__(self, db, rt_db, force_write, verbose):
    self.mps = MPSConfig(args.database[0].name, args.database[0].name.split('.')[0]+'_runtime.db')
    self.session = self.mps.session
    self.rt_session = self.mps.runtime_session
    self.mps_names = MpsName(self.session)
    self.verbose = verbose
    self.force_write = force_write
    self.rt = RuntimeChecker(self.session, self.rt_session, self.verbose)
    
  def __exit__(self):
    self.session.close()
    self.rt_session.close()

  def check_app(self, app_id):
    app = None
    try:
      app = self.session.query(models.ApplicationCard).filter(models.ApplicationCard.global_id==app_id).one()
    except:
      print('ERROR: Cannot find application with global id {}.'.format(app_id))
      return None

    if (len(app.analog_channels) == 0):
      print('ERROR: There are no analog channels defined for this application (global id={})'.\
              format(app_id))
      print('Name: {}'.format(app.name))
      print('Description: {}'.format(app.description))
      print('Crate: {}, Slot: {}'.format(app.crate.get_name(), app.slot_number))
      return None

    print('Name: {}'.format(app.name))
    print('Description: {}'.format(app.description))
    print('Crate: {}, Slot: {}'.format(app.crate.get_name(), app.slot_number))

    return app

  def check_devices(self, app):
    devices = []
    for c in app.analog_channels:
      [device, rt_device] = self.rt.check_device(c.analog_device.id)
      if (rt_device == None):
        return None
      else:
        devices.append([device, rt_device])

    return devices

  def get_restore_list(self, devices):
    """
    Assembles and returns a list of dicts [{ 'device': device, 'pv': pyepicspv, 'value': threshold},...].
    The thresholds in the list are only those that have been set in the past,
    that is given by the '*_active' table field.

    The input parameter devices in a list of pairs [[device, rt_device],...]
    """
    restore_list=[]
    for [d, rt_d] in devices:
      is_bpm = False
      if (d.device_type.name == 'BPMS'):
        is_bpm = True

      threshold_list = self.rt.get_thresholds(d)

      for threshold_item in threshold_list:
        restore_item = {}
        if (threshold_item['active']):
          restore_item['device'] = rt_d
          restore_item['pv'] = threshold_item['pv']
          restore_item['value'] = threshold_item['value']
          restore_list.append(restore_item)
          if (self.verbose):
            print('{}={}'.format(threshold_item['pv'].pvname, threshold_item['value']))

    return restore_list

  def check_pvs(self, restore_list):
    """
    Check if the PVs in the restore list are available
    """
    valid_pvs = True
    bad_pv_names = ''
    for restore_item in restore_list:
      if (restore_item['pv'].host == None):
        valid_pvs = False
        bad_pv_names = '{} * {}\n'.format(bad_pv_names, restore_item['pv'].pvname)
    
    if (not valid_pvs):
      print('ERROR: The following PV(s) cannot be reached, threshold change not allowed:')
      print(bad_pv_names)
      return False

    return True

  def do_restore(self, restore_list):
    for restore_item in restore_list:
      try:
        restore_item['pv'].put(restore_item['value'])
      except epics.ca.CASeverityException:
        if (self.force_write):
          return True
        else:
          print('ERROR: Tried to write to a read-only PV ({}={})'.\
                  format(restore_item['pv'].pvname, restore_item['value']))
          return False
    return True

  def restore(self, app_id):
    app = self.check_app(app_id)
    if (app == None):
      return False

    devices = self.check_devices(app)
    restore_list = self.get_restore_list(devices)
    if (not self.check_pvs(restore_list)):
      return False

    return self.do_restore(restore_list)

  def check(self, app_id):
    self.rt.check_app_thresholds(app_id)
    
#=== MAIN ==================================================================================

parser = argparse.ArgumentParser(description='Restore threshold values from the runtime database',
                                 formatter_class=RawTextHelpFormatter)
parser.add_argument('database', metavar='db', type=file, nargs=1, 
                    help='database file name (e.g. mps_gun.db, where the runtime database is named mps_gun_runtime.db')

parser.add_argument('--app-id', metavar='ID', type=int, nargs='?', help='application global id')
parser.add_argument('-c', action='store_true', default=False, dest='check',
                    help='read back threshold values from PV and compare with runtime database thresholds')
parser.add_argument('-f', action='store_true', default=False, dest='force_write',
                    help='restore thresholds even if PVs are not writable (changes only the database)')
parser.add_argument('-v', action='store_true', default=False,
                    dest='verbose', help='verbose output')

proc = subprocess.Popen('whoami', stdout=subprocess.PIPE)
user = proc.stdout.readline().rstrip()

args = parser.parse_args()

tr = ThresholdRestorer(args.database[0].name,
                       args.database[0].name.split('.')[0]+'_runtime.db',
                       args.force_write, args.verbose)
if (not tr.restore(args.app_id)):
  exit(1)

if (args.check):
  if (not tr.check(args.app_id)):
    exit(2)

