
from mps_database.mps_config import MPSConfig, models, runtime
from mps_database.tools.mps_names import MpsName
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
  std_threshold_tables = ['threshold0','threshold1','threshold2','threshold3',
                          'threshold4','threshold5','threshold6','threshold7']
  alt_threshold_tables = ['threshold_alt0', 'threshold_alt1','threshold_alt2', 'threshold_alt3',
                          'threshold_alt4', 'threshold_alt5','threshold_alt6', 'threshold_alt7']
  lc1_tables = ['threshold_lc1']
  idl_tables = ['threshold_idl']
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

  def get_device_input_id_from_pv(self, pv_name):
    return False

  def get_device_id_from_name(self, name):
    try:
      d = self.session.query(models.Device).filter(models.Device.name==name).one()
      return d.id
    except:
      print('ERROR: Cannot find device "{0}"'.format(name))
      return None

  def get_thresholds(self, device, active_only=True):
    """
    Return a list of all possible thresholds for the specified device, including
    the value/active from the database. This is the format:
    [{
    'pv': pyepics_pv for the threshold PV
    'pv_enable': pyepics_pv for the threshold enable PV
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
      print(('ERROR: Failed to find device id {} in runtime database'.format(device_id)))
      return None

    is_bpm = False
    if (device.device_type.name == 'BPMS'):
      is_bpm = True

    for t_index, t_table in enumerate(self.threshold_tables):
      for integrator in self.integrators:
        if (integrator == 'i3' and is_bpm): # i3 is not valid for BPMs only i0, i1 and i3 (x, y and tmit)
          continue

        for t_type in self.threshold_types:
          threshold_item = {}
          pv_name = self.mps_names.getThresholdPv(self.mps_names.getAnalogDeviceNameFromId(device.id),
                                                  self.threshold_tables_pv[t_index], self.threshold_index[t_index],
                                                  integrator, t_type, is_bpm)
          if (pv_name == None):
            print(('ERROR: Failed to find threshold PV name for device \'{}\' [threshold={}, integrator={}, is_bpm={}]'.\
                    format(device.name, self.threshold_tables_pv[t_index], integrator, is_bpm)))
            return None

          pv_name_enable = pv_name + '_EN'
          if (pv_name):
            threshold_item['db_table'] = t_table
            threshold_item['integrator'] = integrator
            threshold_item['threshold_type'] = t_type
            threshold_item['active'] = bool(getattr(getattr(rt_d, threshold_item['db_table']), '{0}_{1}_active'.\
                                                      format(integrator, t_type)))
            threshold_item['value'] = float(getattr(getattr(rt_d, threshold_item['db_table']), '{0}_{1}'.\
                                                      format(integrator, t_type)))
            if (active_only):
              if (threshold_item['active']):
                threshold_item['pv'] = PV(pv_name)
                threshold_item['pv_enable'] = PV(pv_name_enable)
              else:
                threshold_item['pv'] = None
                threshold_item['pv_enable'] = None
            else:
              threshold_item['pv'] = PV(pv_name)
              threshold_item['pv_enable'] = PV(pv_name_enable)
              
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
      print(('ERROR: Cannot find application with global id {}.'.format(app_id)))
      return False

    if (len(app.analog_channels) > 0):
      for c in app.analog_channels:
        [device, rt_device] = self.check_device(c.analog_device.id)
        if (device == None):
          print('ERROR: Cannot check device')
          return False
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
      print(('ERROR: Failed to find device id {} in database'.format(device_id)))
      return [None, None]

    try:
      rt_device = self.rt_session.query(runtime.Device).\
          filter(runtime.Device.mpsdb_id==device_id).one()
    except:
      print(('ERROR: Failed to find device id {} in runtime database'.format(device_id)))
      return [None, None]

    if (rt_device.mpsdb_name != device.name):
      print('ERROR: Device names are different in MPS database and runtime database:')
      print((' * MPS Database name: {}'.format(device.name)))
      print((' * RT  Database name: {}'.format(rt_device.mpsdb_name)))
      return [None, None]

    return [device, rt_device]

  def check_device_input(self, device_input_id):
    """
    Verify if device_input_id is mapped on both databases.
    Returns None if there is a mismatch, and a pair [device_input, rt_device_input]
    if device_input_id is valid on both
    """
    try:
      device_input = self.session.query(models.DeviceInput).\
          filter(models.DeviceInput.id==device_input_id).one()
    except Exception as ex:
      print(ex)
      print(('ERROR: Failed to find device_input id {} in database'.format(device_input_id)))
      return [None, None]

    try:
      rt_device_input = self.rt_session.query(runtime.DeviceInput).\
          filter(runtime.DeviceInput.mpsdb_id==device_input_id).one()
    except Exception as ex:
      print(ex)
      print(('ERROR: Failed to find device_input id {} in runtime database'.format(device_input_id)))
      return [None, None]

    return [device_input, rt_device_input]

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
      print(('       found {0} devices in config database'.format(len(devices))))
      print(('       found {0} devices in runtime database'.format(len(rt_devices))))
      return False
    if (self.verbose):
      print((' done. Found {} devices.'.format(len(devices))))

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
        print(('       {0} [id={1}] in config database'.format(a[0], a[1])))
        print(('       {0} [id={1}] in runtime database'.format(b[0], b[1])))
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
        print('ERROR: Mismatched devices found')
        print('       {0} [id={1}] in config database'.format(a[0], a[1]))
        print('       {0} [id={1}] in runtime database'.format(b[0], b[1]))
        return False
    if (self.verbose):
      print(' done.')

  def add_device_input_bypass(self, device_input, rt_device_input):
    pv_name = self.mps_names.getDeviceInputName(device_input)
    bypass = runtime.Bypass(device_input=rt_device_input, startdate=int(time.time()),
                            duration=0, pv_name=pv_name)
    self.rt_session.add(bypass)

  def add_analog_bypass(self, device, rt_device):
    # Get the fault inputs that use the analog device
    try:
      fault_inputs = self.session.query(models.FaultInput).filter(models.FaultInput.device_id==device.id).all()
    except:
      print(('ERROR: Failed find fault inputs for device id {} in database'.format(device.id)))
      return None

    # From the fault inputs find which integrators are being used
    fa_names = ['', '', '', '']

    for fi in fault_inputs:
      faults = self.session.query(models.Fault).filter(models.Fault.id==fi.fault_id).all()
      for fa in faults:
        fa_names[fa.get_integrator_index()] = fa.name
    
    if (len(fault_inputs) == 0):
      return None

    for i in range(4):
      pv_name = self.mps_names.getAnalogDeviceName(device)
      if (fa_names[i] == ''):
        pv_name = ''
      else:
        pv_name = pv_name + ':' + fa_names[i]
      bypass = runtime.Bypass(device_id=device.id, startdate=int(time.time()),
                              duration=0, device_integrator=i, pv_name=pv_name)
      self.rt_session.add(bypass)

  def add_runtime_thresholds(self, device):
    t0 = runtime.Threshold0(device=device, device_id=device.id)
    self.rt_session.add(t0)
    t1 = runtime.Threshold1(device=device, device_id=device.id)
    self.rt_session.add(t1)
    t2 = runtime.Threshold2(device=device, device_id=device.id)
    self.rt_session.add(t2)
    t3 = runtime.Threshold3(device=device, device_id=device.id)
    self.rt_session.add(t3)
    t4 = runtime.Threshold4(device=device, device_id=device.id)
    self.rt_session.add(t4)
    t5 = runtime.Threshold5(device=device, device_id=device.id)
    self.rt_session.add(t5)
    t6 = runtime.Threshold6(device=device, device_id=device.id)
    self.rt_session.add(t6)
    t7 = runtime.Threshold7(device=device, device_id=device.id)
    self.rt_session.add(t7)

    t0 = runtime.ThresholdAlt0(device=device, device_id=device.id)
    self.rt_session.add(t0)
    t1 = runtime.ThresholdAlt1(device=device, device_id=device.id)
    self.rt_session.add(t1)
    t2 = runtime.ThresholdAlt2(device=device, device_id=device.id)
    self.rt_session.add(t2)
    t3 = runtime.ThresholdAlt3(device=device, device_id=device.id)
    self.rt_session.add(t3)
    t4 = runtime.ThresholdAlt4(device=device, device_id=device.id)
    self.rt_session.add(t4)
    t5 = runtime.ThresholdAlt5(device=device, device_id=device.id)
    self.rt_session.add(t5)
    t6 = runtime.ThresholdAlt6(device=device, device_id=device.id)
    self.rt_session.add(t6)
    t7 = runtime.ThresholdAlt7(device=device, device_id=device.id)
    self.rt_session.add(t7)

    t = runtime.ThresholdLc1(device=device, device_id=device.id)
    self.rt_session.add(t)

    t = runtime.ThresholdIdl(device=device, device_id=device.id)
    self.rt_session.add(t)

  def create_runtime_database(self):
    print('Creating thresholds/bypass database')

    devices = self.session.query(models.Device).all()
    for d in devices:
      rt_d = runtime.Device(mpsdb_id = d.id, mpsdb_name = d.name)
      self.rt_session.add(rt_d)
      self.rt_session.commit()
      # Add thresholds - if device is analog
      analog_devices = self.session.query(models.AnalogDevice).filter(models.AnalogDevice.id==d.id).all()
      if (len(analog_devices)==1):
        self.add_runtime_thresholds(rt_d)
        self.add_analog_bypass(d, rt_d)

    device_inputs = self.session.query(models.DeviceInput).all()
    for di in device_inputs:
      di_pv = self.mps_names.getDeviceInputNameFromId(di.id)
      rt_di = runtime.DeviceInput(mpsdb_id = di.id, device_id = di.digital_device.id, pv_name = di_pv)
      self.rt_session.add(rt_di)
      self.add_device_input_bypass(di, rt_di)
    self.rt_session.commit()

