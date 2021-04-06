#!/usr/bin/env python

from mps_database.mps_config import MPSConfig, models, runtime
from mps_database.mps_names import MpsName
from mps_database.runtime import *
from runtime_utils import RuntimeChecker
from sqlalchemy import func
import subprocess
import argparse
import time 
import datetime
import sys
import os
import re
import epics
from epics import PV
from argparse import RawTextHelpFormatter

class BypassRestorer:
  def __init__(self, db, rt_db, verbose, force_write, simulate, no_check):
    self.mps = MPSConfig(args.database[0].name, args.database[0].name.split('.')[0]+'_runtime.db')
    self.session = self.mps.session
    self.rt_session = self.mps.runtime_session
    self.mps_names = MpsName(self.session)
    self.rt = RuntimeChecker(self.session, self.rt_session, False)
    self.force_write = force_write
    self.verbose = verbose
    self.simulate = simulate
    self.no_check = no_check

  def __exit__(self):
    self.session.close()
    self.rt_session.close()

  def get_valid_bypasses(self):
    """
    Go through the runtime.bypasses table and builds a list of bypasses to
    be restored based on the current time, bypass start time and duration.

    Returns one list with analog bypasses and another list with digital
    bypasses to be restored:

    analog_list = [{
    'duration': remaining bypass duration in seconds
    'bypd_pv': duration pv
    'byps_pv': status pv
    }, ... ]

    digital_list = [{
    'duration': remaining bypass duration in seconds
    'bypd_pv': duration pv
    'byps_pv': status pv
    'pypv_pv': value pv
    'value': bypass value
    }, ... ]
    """
    # Bypasses must be still valid to be restored
    time_now = int(time.time())

    bypasses = self.rt_session.query(runtime.Bypass).filter(runtime.Bypass.duration>0).all()
    if (self.verbose):
      print('INFO: There are {} bypasses with non-zero duration'.\
              format(len(bypasses)))
    
    analog_bypass_list = []
    digital_bypass_list = []
    for bypass in bypasses:
      bypass_info = {}
      if (bypass.startdate + bypass.duration >= time_now):
        # Remaining duration
        bypass_info['duration'] = bypass.duration - (time_now - bypass.startdate)
        d = datetime.datetime.fromtimestamp(bypass.startdate + bypass.duration)
        bypass_info['expiration_date'] = d.strftime('%Y.%m.%d-%H:%M:%S')
        bypass_info['bypd_pv'] = PV(bypass.pv_name + '_BYPD')
        bypass_info['byps_pv'] = PV(bypass.pv_name + '_BYPS')
        if (bypass.device_input):
          bypass_info['bypv_pv'] = PV(bypass.pv_name + '_BYPV')
          bypass_info['value'] = bypass.value
          digital_bypass_list.append(bypass_info)
        else:
          analog_bypass_list.append(bypass_info)
          
    return [sorted(analog_bypass_list, key=lambda k: k['duration']),
            sorted(digital_bypass_list, key=lambda k: k['duration'])]

  def print_bypass_list(self, bypass_list):
    for b in bypass_list:
      print(' {}: {} (remaining {} seconds)'.format(b['expiration_date'], b['bypd_pv'].pvname, b['duration']))

  def write_pv(self, pv, value):
    if (self.verbose):
      print(' Restoring {}={}'.format(pv.pvname, value))

    try:
      pv.put(value)
    except epics.ca.CASeverityException:
      if (self.force_write):
        return True
      else:
        print('ERROR: Tried to write to a read-only PV ({}={})'.format(pv.pvname, value))
        return False

  def read_pv(self, pv):
    try:
      if (self.verbose):
        sys.stdout.write(' Reading {}'.format(pv.pvname))
      value = pv.get()
      if (self.verbose):
        print('={}'.format(value))
      return value
    except epics.ca.CASeverityException:
      print('ERROR: Failed to read PV ({})'.format(pv.pvname))
      return None


  def restore_bypasses(self, bypass_list, bypass_type = 'analog'):
    """
    Restore the bypasses passed in bypass_list by updating the bypass
    duration and values (if digital). The status of each bypass
    setting is returned in the same bypass_list in the 'byps_status' and
    'bypv_status' fields.

    Returns [ fail_count, bypass_list ], where fail_count the number
    of bypasses that failed to be restored
    """
    if (self.verbose):
      print('Restoring {} bypasses ({}):'.format(bypass_type, len(bypass_list)))
    fail_count = 0
    for b in bypass_list:
      if (bypass_type == 'digital'):
        self.write_pv(b['bypv_pv'], b['value'])
        if (not self.no_check):
          v = self.read_pv(b['bypv_pv'])
          if (v != b['value']):
            b['bypv_status'] = 'FAILED'
            fail_count += 1
          else:
            b['bypv_status'] = 'OK'
        else:
          b['bypv_status'] = 'NO-CHECK'

      self.write_pv(b['bypd_pv'], b['duration'])
      if (not self.no_check):
        v = self.read_pv(b['byps_pv'])
        if (v == 0):
          b['byps_status'] = 'FAILED'
          fail_count += 1
        else:
          b['byps_status'] = 'OK'
      else:
        b['byps_status'] = 'NO-CHECK'

    return [ fail_count, bypass_list ]

  def report(self, fail_count, bypass_list, bypass_type = 'analog'):
    print('{} bypass restore status:'.format(bypass_type.title()))
    if (fail_count > 0):
      print(' Failed to restore {} bypasses'.format(fail_count))

    for b in bypass_list:
      sys.stdout.write(' {}: {} (remaining {} seconds)'.format(b['expiration_date'], b['bypd_pv'].pvname, b['duration']))
      sys.stdout.write(' : [status={}'.format(b['byps_status']))
      if (bypass_type == 'analog'):
        print(']')
      else:
        print(', value={}]'.format(b['bypv_status']))
    return True

  def restore(self):
    [analog_bypass_list, digital_bypass_list] = self.get_valid_bypasses()

    if (self.verbose):
      if (len(analog_bypass_list) > 0):
        print('Valid analog bypasses ({}):'.format(len(analog_bypass_list)))
        self.print_bypass_list(analog_bypass_list)
      if (len(digital_bypass_list) > 0):
        print('Valid digital bypasses ({}):'.format(len(digital_bypass_list)))
        self.print_bypass_list(digital_bypass_list)

    [ fail_count, analog_bypass_list ] = self.restore_bypasses(analog_bypass_list, 'analog')
    self.report(fail_count, analog_bypass_list, 'analog')

    [ fail_count, digital_bypass_list ] = self.restore_bypasses(digital_bypass_list, 'digital')
    self.report(fail_count, digital_bypass_list, 'digital')

    return False

#=== MAIN ==================================================================================

parser = argparse.ArgumentParser(description='Set bypass for analog device (integrator) or device input (digital)',
                                 formatter_class=RawTextHelpFormatter)
parser.add_argument('database', metavar='db', type=file, nargs=1, 
                    help='database file name (e.g. mps_gun.db)')
parser.add_argument('-s', action='store_true', default=False,
                    dest='simulate', help='prints out the list of valid bypasses')
parser.add_argument('-f', action='store_true', default=False,
                    dest='force_write', help='tries to restore bypasses even if PVs are not writable')
parser.add_argument('-v', action='store_true', default=False,
                    dest='verbose', help='verbose output')
parser.add_argument('--no-check', action='store_true', default=False,
                    dest='no_check', help='do *not* verify if bypass operation worked (read back BYPS status PV)')


args = parser.parse_args()
br = BypassRestorer(args.database[0].name, args.database[0].name.split('.')[0]+'_runtime.db',
                    args.verbose, args.force_write, args.simulate, args.no_check)

br.restore()

exit(0)

