
from mps_config import MPSConfig, models, runtime
from mps_names import MpsName
from sqlalchemy import func
import sys
import argparse
import time 
import os
import epics
from epics import PV

class RuntimeChecker:
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

  def __init__(self, session, rt_session, verbose):
    self.session = session
    self.rt_session = rt_session
    self.verbose = verbose
    self.mps_names = MpsName(session)

  def get_device_id_from_name(self, name):
    try:
      d = self.session.query(models.Device).filter(models.Device.name==name).one()
      return d.id
    except:
      print 'ERROR: Cannot find device "{0}"'.format(name)
      return None

  def get_thresholds(self, device):
    """
    Return a list of all possible thresholds for the specified device, including
    the value/active from the database. This is the format:
    [{
    'pv': pyepics_pv for the threshold PV
    'db_table': threshold table name in the runtime database
    'integrator': from the array self.integrators
    'threshold_type': from the array self.threshold_type ('l' or 'h')
    'active': True or False
    'value': threshold value from the database
    }, ...]
    """
    threshold_list=[]

    try:
      rt_d = self.rt_session.query(runtime.Device).\
          filter(runtime.Device.mpsdb_id==device.id).one()
    except:
      print('ERROR: Failed to find device id {} in runtime database'.format(device_id))
      return None

    is_bpm = False
    if (device.device_type.name == 'BPMS'):
      is_bpm = True

    for t_index, t_table in enumerate(self.threshold_tables):
      for t_type in self.threshold_types:
        for integrator in self.integrators:
          threshold_item = {}
          pv_name = self.mps_names.getThresholdPv(self.mps_names.getAnalogDeviceNameFromId(device.id),
                                                  self.threshold_tables_pv[t_index], self.threshold_index[t_index],
                                                  integrator, t_type, is_bpm)
          if (pv_name):
            threshold_item['pv'] = PV(pv_name)
            threshold_item['db_table'] = t_table
            threshold_item['integrator'] = integrator
            threshold_item['threshold_type'] = t_type
            threshold_item['active'] = bool(getattr(getattr(rt_d, threshold_item['db_table']), '{0}_{1}_active'.\
                                                      format(integrator, t_type)))
            threshold_item['value'] = float(getattr(getattr(rt_d, threshold_item['db_table']), '{0}_{1}'.\
                                                      format(integrator, t_type)))

            threshold_list.append(threshold_item)

    return threshold_list

  def check_device_thresholds(self, device):
    threshold_list = self.get_thresholds(device)

    invalid_pvs = False
    invalid_pv_names = ''

    read_pv_error = False
    read_pv_names = ''

    mismatch_value = False
    mismatch_pv_names = ''

    for threshold_item in threshold_list:
      if (threshold_item['active']):
        if (threshold_item['pv'].host == None):
          invalid_pvs = True
          invalid_pv_names = '{} * {}={}\n'.format(bad_pv_names,
                                                   threshold_item['pv'].pvname,
                                                   threshold_item['value'])
        else:
          try:
            pv_value = threshold_item['pv'].get()
          except epics.ca.CASeverityException:
            read_pv_error = True
            read_pv_names = '{} * {}\n'.format(read_pv_names,
                                               threshold_item['pv'].pvname)
            continue

          if (pv_value != threshold_item['value']):
            mismatch_value = True
            mismatch_pv_names = '{} * {} (PV={}, DB={})\n'.\
                format(mismatch_pv_names, threshold_item['pv'].pvname,
                       pv_value, threshold_item['value'])
            
    if (invalid_pvs or read_pv_error or mismatch_value):
      if (invalid_pvs):
        print('ERROR: Cannot reach these PVs:')
        print(invalid_pv_names)
        
      if (read_pv_error):
        print('ERROR: Cannot read these PVs:')
        print(read_pv_names)

      if (mismatch_value):
        print('ERROR: Threshold values are different for these PVs:')
        print(mismatch_pv_names)
      return False

    return True


  def check_app_thresholds(self, app_id):
    """
    Check whether the runtime database thresholds are the same as the values set
    in the SIOCs.
    """
    app = None
    try:
      app = self.session.query(models.ApplicationCard).filter(models.ApplicationCard.global_id==app_id).one()
    except:
      print('ERROR: Cannot find application with global id {}.'.format(app_id))
      return False

    if (len(app.analog_channels) > 0):
      for c in app.analog_channels:
        [device, rt_device] = self.check_device(c.analog_device.id)
        self.check_device_thresholds(device)

    return True

  def check_device(self, device_id):
    """
    Verify if device_id is mapped on both databases.
    Returns None if there is a mismatch, and a pair [device, rt_device]
    if device_id is valid on both
    """
    try:
      device = self.session.query(models.Device).\
          filter(models.Device.id==device_id).one()
    except:
      print('ERROR: Failed to find device id {} in database'.format(device_id))
      return None

    try:
      rt_device = self.rt_session.query(runtime.Device).\
          filter(runtime.Device.mpsdb_id==device_id).one()
    except:
      print('ERROR: Failed to find device id {} in runtime database'.format(device_id))
      return None

    if (rt_device.mpsdb_name != device.name):
      print('ERROR: Device names are different in MPS database and runtime database:')
      print(' * MPS Database name: {}'.format(device.name))
      print(' * RT  Database name: {}'.format(rt_device.mpsdb_name))
      return None

    return [device, rt_device]

  def check_databases(self):
    self.mps_name = MpsName(self.session)

    # First check the devices in both databases
    devices = self.session.query(models.Device).all()
    rt_devices = self.rt_session.query(runtime.Device).all()

    if (self.verbose):
      sys.stdout.write('Checking number of devices in both databases...')

    if (len(devices) != len(rt_devices)):
      print('')
      print('ERROR: Number of devices in databases must be the same')
      print('       found {0} devices in config database'.format(len(devices)))
      print('       found {0} devices in runtime database'.format(len(rt_devices)))
      return False
    if (self.verbose):
      print(' done. Found {} devices.'.format(len(devices)))

    # Extract device_ids and names and sort
    d = [ [i.id, i.name] for i in devices ]
    d = sorted(d, key=lambda v: v[0])

    rt_d = [ [i.mpsdb_id, i.mpsdb_name] for i in rt_devices ]
    rt_d = sorted(rt_d, key=lambda v: v[0])

    # Compare one by one the devices, they must be exactly the same
    if (self.verbose):
      sys.stdout.write('Checking device names and ids in both databases...')
    for a, b in zip(d, rt_d):
      if (a[0] != b[0] or a[1] != b[1]):
        print('')
        print('ERROR: Mismatched devices found')
        print('       {0} [id={1}] in config database'.format(a[0], a[1]))
        print('       {0} [id={1}] in runtime database'.format(b[0], b[1]))
        return False
    if (self.verbose):
      print(' done.')

    # Now check the device_inputs (i.e. digital devices)
    device_inputs = self.session.query(models.DeviceInput).all()
    rt_device_inputs = self.rt_session.query(runtime.DeviceInput).all()

    # Extract device_ids and names and sort
    di = [ [i.id, self.mps_name.getDeviceInputName(i)] for i in device_inputs ]
    d.sort()

    rt_di = [ [i.mpsdb_id, i.pv_name] for i in rt_device_inputs ]
    rt_di.sort()

    # Compare one by one the device inputs, they must be exactly the same
    if (self.verbose):
      sys.stdout.write('Checking device inputs (digital channels) names and ids in both databases...')
    for a, b in zip(di, rt_di):
      if (a[0] != b[0] or a[1] != b[1]):
        print 'ERROR: Mismatched devices found'
        print '       {0} [id={1}] in config database'.format(a[0], a[1])
        print '       {0} [id={1}] in runtime database'.format(b[0], b[1])
        return False
    if (self.verbose):
      print(' done.')
