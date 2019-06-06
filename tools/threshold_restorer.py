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
  Restore thresholds of analog devices - using latest thresholds saved in database
  """
  def __init__(self, db=None, rt_db=None, force_write=False, verbose=False, mps=None):
    if (db != None and rt_db != None): 
      self.mps = MPSConfig(db, rt_db)
    elif (mps != None):
      self.mps = mps
    else:
      raise ValueError('MPS database instance not specified')

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
    if (self.verbose):
      sys.stdout.write('Checking app_id {}... '.format(app_id))
    
    app = None
    try:
      app = self.session.query(models.ApplicationCard).filter(models.ApplicationCard.global_id==app_id).one()
    except:
      print('ERROR: Cannot find application with global id {}.'.format(app_id))
      return None

    if (self.verbose):
      print('found')


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
    if (self.verbose):
      sys.stdout.write('Checking devices... ')

    devices = []
    for c in app.analog_channels:
      [device, rt_device] = self.rt.check_device(c.analog_device.id)
      if (rt_device == None):
        return None
      else:
        devices.append([device, rt_device])

    if (self.verbose):
      print('done.')

    return devices

  def get_restore_list(self, devices):
    """
    Assembles and returns a list of dicts [{ 'device': device, 'pv': pyepicspv, 'value': threshold},...].
    The thresholds in the list are only those that have been set in the past,
    that is given by the '*_active' table field.

    The input parameter devices in a list of pairs [[device, rt_device],...]
    """
    if (self.verbose):
      sys.stdout.write('Retrieving thresholds... ')

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

    if (self.verbose):
      print('done.')

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
    if (self.verbose):
      print('Starting restore process')

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

    if (self.verbose):
      print('Finished restore process')

    return True

  def release(self, app):
    release_pv = PV('{}:THR_LOADED'.format(app.get_pv_name()))

    if (self.verbose):
      sys.stdout.write('Releasing IOC (setting {})...'.format(release_pv.pvname))

    # do release
    if (release_pv.host == None):
      print('ERROR: Failed to read relase PV {}'.format(release_pv.pvname))
      return False

    try:
      release_pv.put(1)
    except epics.ca.CASeverityException:
      print('ERROR: Tried to write to a read-only PV ({}=1)'.\
              format(release_pv.pvname))
      return False
      
    if (self.verbose):
      print(' done.')

  def restore(self, app_id, release=False):
    app = self.check_app(app_id)
    if (app == None):
      return False

    devices = self.check_devices(app)
    if (devices == None):
      print('ERROR: found no devices in databases {}'.format(app_id))
      return False
      
    restore_list = self.get_restore_list(devices)
    if (not self.check_pvs(restore_list)):
      return False

    if (not self.do_restore(restore_list)):
      return False

    if (release):
      self.release(app)

    return True

  def check(self, app_id):
    return self.rt.check_app_thresholds(app_id)
    
