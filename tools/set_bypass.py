#!/usr/bin/env python

from mps_config import MPSConfig, models, runtime
from mps_names import MpsName
from runtime import *
from runtime_utils import RuntimeChecker
from sqlalchemy import func
import subprocess
import argparse
import time 
import sys
import os
import re
import epics
from epics import PV
from argparse import RawTextHelpFormatter

class BypassManager:
  def __init__(self, db, rt_db, verbose, force_write):
    self.mps = MPSConfig(args.database[0].name, args.database[0].name.split('.')[0]+'_runtime.db')
    self.session = self.mps.session
    self.rt_session = self.mps.runtime_session
    self.mps_names = MpsName(self.session)
    self.rt = RuntimeChecker(self.session, self.rt_session, False)
    self.force_write = force_write
    self.verbose = verbose

  def __exit__(self):
    self.session.close()
    self.rt_session.close()

  def set_digital_bypass(self, device_input_id, device_input_pv, user, reason, duration, value):
    """
    Set bypass for a digital input (device_input), which is one of potetially multiple
    inputs to a digital device (e.g. YAG01 device has 2 inputs, IN_LMTSW and OUT_LMTSW.

    Functionality similar to set_analog_bypass().
    """
    if (value != None):
      if (value != 0 and value != 1):
        print('ERROR: Expected value for digital bypass must be 0 or 1, value={} is not supported'.\
                format(value))
        return False
    
    # This is the current time
    time_now = int(time.time())

    if (device_input_id < 0 or device_input_id == None):
      device_input_id = self.rt.get_device_id_from_name(device_name)
      if (device_input_id == None):
        return False

    [device_input, rt_device_input] = self.rt.check_device_input(device_input_id)
    if (device_input == None):
      return False

    if (self.set_bypass(rt_device_input.bypass, time_now, user, reason, duration, 'digital', value)):
      return True
    else:
      return False

    return True

  def set_analog_bypass(self, device_id, device_name, integrator, user, reason, duration):
    """
    Set bypass for an analog device, specified by the ID or NAME
  
    Check if there is an active bypass - i.e. if the bypass.duration database
    entry is populated, then check if the new duration goes beyond. If that is 
    the case then extend the bypass. If duration is lesser or equal than the
    current one don't update.
    
    If the specified duration is zero, then if there is an active bypass it \
    should be cancelled.    
    """
    # This is the current time
    time_now = int(time.time())

    if (device_id < 0 or device_id == None):
      device_id = self.rt.get_device_id_from_name(device_name)
      if (device_id == None):
        return False

    [device, rt_device] = self.rt.check_device(device_id)
    if (device == None):
      return False

    # Select bypass based on the specified integrator
    for b in rt_device.bypasses:
      if (b.device_integrator == integrator):
        bypass = b

    if (self.set_bypass(bypass, time_now, user, reason, duration, 'analog')):
      return True
    else:
      return False

  def write_pv(self, pv, value):
    if (self.verbose):
      print('INFO: Writing {}={}'.format(pv.pvname, value))

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
        sys.stdout.write('INFO: Reading {}'.format(pv.pvname))
        value = pv.get()
      if (self.verbose):
        print('={}'.format(value))
      return value
    except epics.ca.CASeverityException:
      print('ERROR: Failed to read PV ({})'.format(pv.pvname))
      return None

  def check_digital_bypass_pvs(self, bypass):
    bad_return = [None, None, None]
    bypd_pv = PV(bypass.pv_name + '_BYPD')
    byps_pv = PV(bypass.pv_name + '_BYPS')
    bypv_pv = PV(bypass.pv_name + '_BYPV')
    if (bypd_pv.host == None):
      print('ERROR: Cannot reach PV {}, bypass not activated'.format(bypd_pv.pvname))
      return bad_return

    if (byps_pv.host == None):
      print('ERROR: Cannot reach PV {}, bypass not activated'.format(byps_pv.pvname))
      return bad_return

    if (bypv_pv.host == None):
      print('ERROR: Cannot reach PV {}, bypass not activated'.format(bypv_pv.pvname))
      return bad_return

    return [bypd_pv, byps_pv, bypv_pv]

  def check_analog_bypass_pvs(self, bypass):
    bad_return = [None, None]
    bypd_pv = PV(bypass.pv_name + '_BYPD')
    byps_pv = PV(bypass.pv_name + '_BYPS')

    if (bypd_pv.host == None):
      print('ERROR: Cannot reach PV {}, bypass not activated'.format(bypd_pv.pvname))
      return bad_return

    if (byps_pv.host == None):
      print('ERROR: Cannot reach PV {}, bypass not activated'.format(byps_pv.pvname))
      return bad_return

    return [bypd_pv, byps_pv]

  def write_bypass_pv(self, bypass, bypd_pv, byps_pv, bypv_pv, duration_value, expected_status_value, bypass_value=None):
    if (bypv_pv != None and bypass_value != None):
      if self.write_pv(bypv_pv, bypass_value):
        v = self.read_pv(bypv_pv)
        if (v != bypass_value):
          print('ERROR: Failed to set bypass value to {}={}, bypass not completed'.\
                  format(bypv_pv.pvname, bypass_value))
          return False

    if self.write_pv(bypd_pv, duration_value):
      v = self.read_pv(byps_pv)
      if (v != expected_status_value):
        print('ERROR: Bypass change for {} requested, however the status PV {}={} does not have the expected value {}.\nOperation failed.'.\
                format(bypass.pv_name, byps_pv.pvname, v, expected_status_value))
        return False
    return True

  def set_bypass(self, bypass, time_now, user, reason, duration, bypass_type, bypass_value=None):
    # Bypass would expire at
    new_expiration = time_now + duration

    if (bypass_type == 'analog'):
      [bypd_pv, byps_pv] = self.check_analog_bypass_pvs(bypass)
      if (bypd_pv == None):
        return False
      bypv_pv = None
    else:
      [bypd_pv, byps_pv, bypv_pv] = self.check_digital_bypass_pvs(bypass)
      if (bypd_pv == None):
        return False
    
    # Set bypass if new expiration date is greater than existing
    prev_expiration = bypass.startdate + bypass.duration
    if (duration == 0):
      if (self.write_bypass_pv(bypass, bypd_pv, byps_pv, duration, 0)):
        if (bypass_value != None):
          bypass.value = bypass_value
        bypass.duration = duration
        self.rt_session.commit()
        self.add_history(user, reason, bypass)
      else:
        print('ERROR: Bypass *not* cancelled.')
        return False
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

      if (self.write_bypass_pv(bypass, bypd_pv, byps_pv, bypv_pv, duration, 1, bypass_value)):
        bypass.duration = duration
        if (bypass_value != None):
          bypass.value = bypass_value
        self.rt_session.commit()
        self.add_history(user, reason, bypass)
      else:
        print('ERROR: Bypass *not* enabled.')
        return False

      bypass.startdate = time_now
      bypass.duration = duration
      self.rt_session.commit()
    else:
      print 'WARN: Specified bypass expiration date is the same as before'
      return False

    return True

  def add_history(self, user, reason, bypass):
    bypass_hist = BypassHistory(user=user, reason=reason, device_id=bypass.device_id,
                                device_input_id=bypass.device_input_id, startdate=bypass.startdate,
                                duration=bypass.duration)
    self.rt_session.add(bypass_hist)
    self.rt_session.commit()

    return True

#=== MAIN ==================================================================================

parser = argparse.ArgumentParser(description='Set bypass for analog device (integrator) or device input (digital)',
                                 formatter_class=RawTextHelpFormatter)
parser.add_argument('database', metavar='db', type=file, nargs=1, 
                    help='database file name (e.g. mps_gun.db)')
parser.add_argument('--reason', metavar='Reason for the bypass setting', type=str, nargs=1,
                    help='reason for the threshold change', required=True)
parser.add_argument('--time', metavar='seconds', type=int, nargs=1,
                    help='Bypass duration is seconds, starting from now.\n' +
                    'Use zero seconds to cancel bypass', required=True)
parser.add_argument('-f', action='store_true', default=False,
                    dest='force_write', help='Change thresholds even if PVs are not writable (changes only the database)')
parser.add_argument('-v', action='store_true', default=False,
                    dest='verbose', help='verbose output')


top_group_list = parser.add_mutually_exclusive_group()
group_list = top_group_list.add_mutually_exclusive_group()
group_list_analog = group_list.add_mutually_exclusive_group()
group_list_analog.add_argument('--analog-device-id', metavar='ID', type=int, nargs=1,
                               help='Database id for the device - must be analog device')
group_list_analog.add_argument('--analog-device-name', metavar='NAME', 
                               type=str, nargs=1, help='Analog device name as found in the MPS database (e.g. BPM1B)')
parser.add_argument('--integrator', metavar='INDEX', type=int, nargs=1,
                    help='analog device integrator (0..3), for BPMs: X=0, Y=1, TMIT=2')
group_list_digital = group_list.add_mutually_exclusive_group()
group_list_digital.add_argument('--device-input-id', metavar='ID', type=int, nargs=1,
                                help='Database id for the device input - use for digital devices')
group_list_digital.add_argument('--device-input-pv', metavar='PV', 
                               type=str, nargs=1, help='Device input PV (e.g. PROF:GUNB:753:IN_SWITCH)')
parser.add_argument('--value', metavar='0 or 1', type=int, nargs=1,
                    help='Expected digital value')

proc = subprocess.Popen('whoami', stdout=subprocess.PIPE)
user = proc.stdout.readline().rstrip()

args = parser.parse_args()

bm = BypassManager(args.database[0].name, args.database[0].name.split('.')[0]+'_runtime.db',
                   args.verbose, args.force_write)

if (args.analog_device_id != None or args.analog_device_name != None):
  if (not args.integrator):
    print('ERROR: Must specify an integrator for analog devices (--integrator switch)')
    exit(1)
  else:
    if (args.analog_device_id == None):
      analog_device_id = None
    else:
      analog_device_id = int(args.analog_device_id[0])

    if (args.analog_device_name == None):
      analog_device_name = None
    else:
      analog_device_name = args.analog_device_name[0]

    if (not bm.set_analog_bypass(analog_device_id, analog_device_name,
                                 int(args.integrator[0]), user, args.reason[0], int(args.time[0]))):
      exit(2)

if (args.device_input_id or args.device_input_pv):
  value = None
  if (args.value != None):
    value = int(args.value[0])

  if (not bm.set_digital_bypass(int(args.device_input_id[0]), args.device_input_pv,
                                user, args.reason[0], int(args.time[0]), value)):
    exit(3)

exit(0)

