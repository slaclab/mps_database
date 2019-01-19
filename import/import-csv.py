#!/usr/bin/env python
from mps_config import MPSConfig, models, runtime
from sqlalchemy import MetaData
from mps_names import MpsName
import argparse
import time
import yaml
import os

class DatabaseImporter:
  conf = None # MPSConfig
  session = None
  beam_destinations = []
  verbose = False
  database_file_name = None

  def __init__(self, file_name, runtime_file_name, verbose, clear_all=True):
    self.database_file_name = file_name
    self.conf = MPSConfig(file_name, runtime_file_name)
    if (clear_all):
      self.conf.clear_all()
    self.session = self.conf.session
    self.session.autoflush=False
#    self.session.autoflush=True
    self.verbose = verbose

    self.rt_session = self.conf.runtime_session

  def __del__(self):
    self.session.commit()
 
  def reopen(self):
    self.session.commit()
    self.session = None
    self.rt_session.commit()
    self.rt_session = None
    self.conf = None
    self.conf = MPSConfig(self.database_file_name)
    self.session = self.conf.session
    self.session.autoflush=False    
    self.rt_session = self.conf.runtime_session
    self.rt_session.autoflush=False    

  def add_crates(self, file_name):
    if self.verbose:
      print "Adding crates... {0}".format(file_name)
    f = open(file_name)

    line = f.readline().strip()
    fields=[]
    for field in line.split(','):
      fields.append(str(field).lower())

    while line:
      crate_info={}
      line = f.readline().strip()

      if line:
        field_index = 0
        for property in line.split(','):
          crate_info[fields[field_index]]=property
          field_index = field_index + 1

        ln = models.LinkNode(area=crate_info['ln_area'], location=crate_info['ln_location'],
                             cpu='cpu-{0}-spXX'.format(crate_info['ln_location'].lower()),
                             group=crate_info['group'], group_link=crate_info['group_link'],
                             group_link_destination=crate_info['group_link_destination'],
                             group_drawing=crate_info['network_drawing'])
        self.session.add(ln)

        crate = models.Crate(crate_id=crate_info['crate_id'],
                             num_slots=crate_info['num_slots'],
                             shelf_number=int(crate_info['shelf_number']),
                             location=crate_info['location'],
                             rack=crate_info['rack'],
                             elevation=crate_info['elevation'],
                             sector=crate_info['sector'],
                             link_node=ln)
        self.session.add(crate)
      
    self.session.commit()
    f.close()


  def add_app_types(self, file_name):
    f = open(file_name)

    line = f.readline().strip()
    fields=[]
    for field in line.split(','):
      fields.append(str(field).lower())

    while line:
      app_type_info={}
      line = f.readline().strip()

      if line:
        field_index = 0
        for property in line.split(','):
          app_type_info[fields[field_index]]=property
          field_index = field_index + 1


#        print app_type_info
        app_type = models.ApplicationType(number=app_type_info['number'],
                                          name=app_type_info['name'],
                                          digital_channel_count=app_type_info['digital_channel_count'],
                                          digital_channel_size=app_type_info['digital_channel_size'],
                                          digital_out_channel_count=app_type_info['digital_out_channel_count'],
                                          digital_out_channel_size=app_type_info['digital_out_channel_size'],
                                          analog_channel_count=app_type_info['analog_channel_count'],
                                          analog_channel_size=app_type_info['analog_channel_size'])
        self.session.add(app_type)
      
    self.session.commit()
    f.close()

  def add_cards(self, file_name):
    f = open(file_name)

    line = f.readline().strip()
    fields=[]
    for field in line.split(','):
      fields.append(str(field).lower())

    while line:
      app_card_info={}
      line = f.readline().strip()

      if line:
        field_index = 0
        for property in line.split(','):
          app_card_info[fields[field_index]]=property
          field_index = field_index + 1

        app_card_type = self.session.query(models.ApplicationType).\
            filter(models.ApplicationType.number==app_card_info['type_number']).one()

        try:
          app_crate = self.session.query(models.Crate).\
              filter(models.Crate.id==app_card_info['crate_number']).one()
        except:
          print('ERROR: Cannot find crate with number {0}, exiting...'.format(app_card_info['crate_number']))

        app_card = models.ApplicationCard(name=app_card_info['name'],
                                          number=int(app_card_info['number']),
                                          area=app_card_info['area'],
                                          location=app_card_info['location'],
                                          type=app_card_type,
                                          slot_number=int(app_card_info['slot']),
                                          amc=int(app_card_info['amc']),
                                          global_id=int(app_card_info['global_id']),
                                          description=app_card_info['description'])

        app_crate.cards.append(app_card)
        self.session.add(app_card)

    self.session.commit()
    f.close()

  def add_device_types(self, file_name):
    f = open(file_name)

    line = f.readline().strip()
    fields=[]
    for field in line.split(','):
      fields.append(str(field).lower())

    while line:
      device_type_info={}
      line = f.readline().strip()

      if line:
        field_index = 0
        for property in line.split(','):
          device_type_info[fields[field_index]]=property
          field_index = field_index + 1

        device_type = models.DeviceType(name=device_type_info['name'],
                                        description=device_type_info['description'],
                                        num_integrators=int(device_type_info['num_integrators']))

        self.session.add(device_type)

    self.session.commit()
    f.close()

# linac = models.BeamDestination(name="LINAC", description="Linac destination", destination_mask=0x01)
  def add_beam_destinations(self, file_name):
    f = open(file_name)

    line = f.readline().strip()
    fields=[]
    for field in line.split(','):
      fields.append(str(field).lower())

    while line:
      destination_info={}
      line = f.readline().strip()

      if line:
        field_index = 0
        for property in line.split(','):
          destination_info[fields[field_index]]=property
          field_index = field_index + 1

        self.beam_destinations.append(destination_info['name'])
        beam_destination = models.BeamDestination(name=destination_info['name'],
                                                  description=destination_info['description'],
                                                  destination_mask=int(destination_info['destination_mask']))

        self.session.add(beam_destination)

    self.session.commit()
    f.close()

#class_0 = models.BeamClass(number=0,name="Power Class 0",description="No Beam",
#                              integration_window=10, total_charge=100000, min_period=1)
  def add_beam_classes(self, file_name):
    f = open(file_name)

    line = f.readline().strip()
    fields=[]
    for field in line.split(','):
      fields.append(str(field).lower())

    while line:
      class_info={}
      line = f.readline().strip()

      if line:
        field_index = 0
        for property in line.split(','):
          class_info[fields[field_index]]=property
          field_index = field_index + 1

        beam_class = models.BeamClass(number=class_info['number'],
                                      name=class_info['name'],
                                      description=class_info['description'],
                                      integration_window=int(class_info['integration_window']),
                                      total_charge=int(class_info['total_charge']),
                                      min_period=int(class_info['min_period']))

        self.session.add(beam_class)

    self.session.commit()
    f.close()

  def check_device_type(self, file_name):
    f = open(file_name)
    line = f.readline().strip()
    fields=[]
    has_measured_device_type = False
    for field in line.split(','):
      fields.append(str(field).lower())
      lower_case_field = str(field).lower()
       # check if device is measuring some other device
      if (lower_case_field == 'measured_device_type_id'):
        has_measured_device_type = True

    type_info={}
    while line:
      line = f.readline().strip()

      if line:
        field_index = 0
        for property in line.split(','):
          type_info[fields[field_index]]=property
          field_index = field_index + 1

        try:
          device_type = self.session.query(models.DeviceType).\
              filter(models.DeviceType.name==type_info['name']).one()
        except:
          print('ERROR: Cannot find device type with name {0}, exiting...'.format(type_info['name']))
          return None
    f.close()

    if has_measured_device_type:
      return [device_type,type_info['evaluation'],type_info['measured_device_type_id']]
    else:
      return [device_type,type_info['evaluation'],None]

  def getFault(self, faults, device_state):
    print ' Looking for "{0}"'.format(device_state)
    # Find the proper fault for the mitigation 
    device_fault=None
    found=False

    for x in faults:
      print ' ' + str(faults[x]['states'])
      found=True
      try: 
        faults[x]['states'].index(device_state)
      except:
        found=False

      if found:
        device_fault = faults[x]['fault']

    return device_fault

  def add_device_states(self, file_name, device_type, add_faults=True):
    f = open(file_name)
    line = f.readline().strip()
    fields=[]
    for field in line.split(','):
      fields.append(str(field).lower())

    faults={}
    device_states={}
    while line:
      state_info={}
      line = f.readline().strip()

      if line:
        field_index = 0
        for property in line.split(','):
          state_info[fields[field_index]]=property
          field_index = field_index + 1
          
        device_state = models.DeviceState(name=state_info['name'],
                                          device_type=device_type,
                                          description=state_info['description'],
                                          value=int(state_info['value']),
                                          mask=int(state_info['mask']))
        device_states[state_info['name']]=device_state#state_info

        if (add_faults):
          if (state_info['fault'] != '-'):
            fault_name = state_info['fault']
            fault_desc = state_info['fault_description']
    #        print '{0}: {1}'.format(fault_name,fault_desc)
            if (not fault_name in faults):
              fault = models.Fault(name=fault_name, description=fault_desc)
              self.session.add(fault)
              faults[fault_name]={}
              faults[fault_name]['name']=fault_name
              faults[fault_name]['desc']=fault_desc
              faults[fault_name]['states']=[]
              faults[fault_name]['states'].append(state_info['name'])
              faults[fault_name]['fault']=fault
            else:
              faults[fault_name]['states'].append(state_info['name'])

        self.session.add(device_state)

    #    print device_states
    print faults
    self.session.commit()
    f.close()

    return faults, device_states

  #
  # Returns a dictionary with the mitigation rules for a device type,
  # each entry is keyed on the destination (e.g. HXU, SXU, Linac),
  # the data for each destination is another dictionary, where each
  # key is the device state name, the data contains the mitigation
  # information. Example for profile monitor, for the Linac destination
  # only (in YAML):
  # Linac:
  #  Broken:
  #    device_location: Linac
  #    device_state_number: '4'
  #    diag0: '-'
  #    fault_description: Linac Screen Fault
  #    hxu: '-'
  #    linac: '1'
  #    state_name: Broken
  #    sxu: '-'
  #  In:
  #    device_location: Linac
  #    device_state_number: '2'
  #    diag0: '-'
  #    fault_description: Linac Screen Fault
  #    hxu: '-'
  #    linac: '2'
  #    state_name: In
  #    sxu: '-'
  #  Moving:
  #    device_location: Linac
  #    device_state_number: '3'
  #    diag0: '-'
  #    fault_description: Linac Screen Fault
  #    hxu: '-'
  #    linac: '1'
  #    state_name: Moving
  #    sxu: '-' 
  def read_mitigation(self, file_name):
    if self.verbose:
      print '  Mitigation actions:'
    f = open(file_name)
    line = f.readline().strip()
    fields = []
    for field in line.split(','):
      fields.append(str(field).lower())
    location = None
    mitigation={}
    while line:
      mitigation_info={}
      line = f.readline().strip()
      if line:
        field_index = 0
        for property in line.split(','):
          mitigation_info[fields[field_index]]=property
          field_index = field_index + 1

        if location != mitigation_info['device_location']:
          mitigation[mitigation_info['device_location']]={}
          location = mitigation_info['device_location']
        mitigation[mitigation_info['device_location']][mitigation_info['state_name']]=mitigation_info

        if self.verbose:
          print "  + {0}".format(mitigation_info['device_location'])

    f.close()
    
#    print yaml.dump(mitigation, default_flow_style=False)
    return mitigation

  def read_conditions(self, file_name):
    f = open(file_name)
    line = f.readline().strip()
    fields = []
    for field in line.split(','):
      fields.append(str(field).lower())
    location = None
    condition={}
    while line:
      condition_info={}
      line = f.readline().strip()
      if line:
        field_index = 0
        for property in line.split(','):
          condition_info[fields[field_index]]=property
          field_index = field_index + 1

        condition[condition_info['state_name']]=condition_info

    f.close()
#    print yaml.dump(condition, default_flow_style=False)
    return condition

  # For a condition with single input, find with device is 
  # used as input - this is used for adding ignore conditions
  # based on device area and location.
  def find_condition_input_device(self, condition):
    # Condition must have single condition_input
    try: 
      inputs = self.session.query(models.ConditionInput).\
          filter(models.ConditionInput.condition_id==condition.id).all()

    except:
      print('ERROR: no inputs found for condition {0}.'.format(condition.name))
      return

    if (len(inputs) > 1):
      print('ERROR: too many inputs ({0}) found for condition {1}.'.format(len(inputs), condition.name))

    # Now find the fault state for the input
    try:
      fault_state = self.session.query(models.FaultState).\
          filter(models.FaultState.id==inputs[0].fault_state.id).one()
    except:
      print('ERROR: cannot find fault_state for condition {0}.'.format(condition.name))

    # Find the fault...
    try:
      fault = self.session.query(models.Fault).\
          filter(models.Fault.id==fault_state.fault_id).one()
    except:
      print('ERROR: cannot find fault for condition {0}.'.format(condition.name))

    # Find the fault_input... must be a single input
    if (len(fault.inputs) > 1):
      print('ERROR: too many inputs ({0}) found for fault {1} that causes condition {2}.'.format(len(inputs), fault.name, condition.name))
    elif (len(fault.inputs) == 0):
      print('ERROR: no many inputs ({0}) found for fault {1} that causes condition {2}.'.format(len(inputs), fault.name, condition.name))

    # Finally get the device that causes triggers the condition
    device = None
    try:
      device = self.session.query(models.Device).\
          filter(models.Device.id==fault.inputs[0].device_id).one()
    except:
      print('ERROR: cannot find device that causes for condition {0}.'.format(condition.name))

    return device

  # Check if the device in the 'cond_area' should be used
  # as ignore condition for the device in 'device_area'
  def check_area_order(self, cond_area, device_area):
    cond = False
    if (device_area.upper() == 'DIAG0' and
        (cond_area.upper() == 'GUNB' or
         cond_area.upper() == 'HTR' or
         cond_area.upper() == 'LR00')):
      cond = True
    elif (device_area.upper().endswith('H') and
          (not cond_area.upper().endswith('S'))):
      cond = True
    elif (device_area.upper().endswith('S') and
          (not cond_area.upper().endswith('H'))):
      cond = True
    elif (cond_area != 'DIAG0'):
      cond = True

    return cond
      
  def add_ignore_conditions_analog(self, device):
    try:
      conditions = self.session.query(models.Condition).all()
    except:
      print('INFO: Found no conditions to ignore')
      return

    for cond in conditions:
      cond_device = self.find_condition_input_device(cond)
      if (cond_device != None):
        # The location of the cond_device must be before the location of the device
        # to be ignored
        try:
          cond_device_z = float(cond_device.z_location)
          device_z = float(device.z_location)
          if (cond_device_z < device_z):
            if (self.check_area_order(cond_device.area, device.area)):
              #            print '{0}, {1}:{2}, {3}:{4}'.format(cond.name, cond_device.name, cond_device.z_location, device.name, device.z_location)
              ignore_condition = models.IgnoreCondition(condition=cond, analog_device=device)    
        except:
          print 'WARN: invalid z_location condition_device={0}, device={1}'.format(cond_device.z_location, device.z_location)


  def add_analog_device(self, directory, card_name, add_ignore=False):
    print 'Adding ' + directory
    file_name = directory + '/DeviceType.csv'
    [device_type, evaluation_string, measured_device_type_id] = self.check_device_type(file_name)
    if device_type == None:
      return

    file_name = directory + '/DeviceStates.csv'
    [faults, device_states] = self.add_device_states(file_name, device_type)

    # Read AnalogChannels, each device has one channel
    file_name = directory + '/AnalogChannels.csv'
    f = open(file_name)
    line = f.readline().strip()
    fields=[]
    for field in line.split(','):
      fields.append(str(field).lower())

    channel={}
    while line:
      channel_info={}
      line = f.readline().strip()

      if line:
        field_index = 0
        for property in line.split(','):
          channel_info[fields[field_index]]=property
          field_index = field_index + 1
          
        channel[channel_info['name']]=channel_info

    f.close()

    # Read Mitigation list
    file_name = directory + '/Mitigation.csv'
    mitigation = self.read_mitigation(file_name)

    # Devices!
    file_name = directory + '/Devices.csv'
    f = open(file_name)
    line = f.readline().strip()
    fields=[]
    for field in line.split(','):
      fields.append(str(field).lower())

    while line:
      device_info={}
      line = f.readline().strip()

      if line:
        field_index = 0
        for property in line.split(','):
          device_info[fields[field_index]]=property
          field_index = field_index + 1
          
        try:
          app_card = self.session.query(models.ApplicationCard).\
              filter(models.ApplicationCard.id==int(device_info['application_card_number'])).one()
          if app_card.name != card_name:
            print('ERROR: analog device ({0}) assigned to unexpected card type ({1}), expected {2} card'.format(device_info['device'], app_card.name, card_name))
            return
        except:
          print('ERROR: Cannot find application_card with id {0}, exiting...'.format(device_info['application_card_number']))
          return

        # there must be only one channel
        if len(channel) != 1:
          print 'ERROR: too many channels defined for AnalogDevice'
          return

        for key in channel:
          channel_name = key
        mps_channel_index = channel[channel_name]['mps_channel_#']
        channel_number = int(device_info['mps_channel_#' + mps_channel_index])

        analog_channel = models.AnalogChannel(name=channel[key]['name'],
                                              number=channel_number, card_id=app_card.id)
        self.session.add(analog_channel)

        device = models.AnalogDevice(name=device_info['device'],
                                     device_type=device_type,
                                     channel=analog_channel,
                                     card=app_card,
                                     position=device_info['position'],
                                     z_location=device_info['linac_z'],
                                     description=device_info['device'] + ' ' + device_type.description,
                                     area=device_info['area'],
                                     evaluation=1) # Fast evaluation
        if (self.verbose):
          print 'Analog Channel: ' + device_info['device']

        self.session.add(device)
#        self.session.commit()

        # If device should be ignored, add conditions
        if (add_ignore):
          self.add_ignore_conditions_analog(device)

        # For each device - create a Faults, FaultInputs, FaultStates and the AllowedClasses
        if device_info['fault'] != 'all':
          device_fault = self.getFault(faults, device_info['fault'])
          if (device_fault == None):
            print 'ERROR: Failed to find Fault for device "{0}"'.format(device_info['name'])
            exit(-1)
#          device_fault = models.Fault(name=device_info['fault'], description=device_info['device'] + ' Fault')
#          self.session.add(device_fault)

          device_fault_input = models.FaultInput(bit_position=0, device=device, fault=device_fault)
          self.session.add(device_fault_input)

          # FaultStates (given by the Mitigation.csv file), entries whose Device_Location matches the device 
          for k in mitigation:
            if device_info['mitigation'] == k:
              for m in mitigation[device_info['mitigation']]:
                fault_state = models.FaultState(device_state=device_states[m], fault=device_fault)
                self.session.add(fault_state)

                # Add the AllowedClasses for each fault state (there may be multiple per FaultState)
                for d in self.beam_destinations:
                  power_class_str = mitigation[device_info['mitigation']][device_states[m].name][d.lower()]
                  if (power_class_str != '-'):
                    beam_class = self.session.query(models.BeamClass).\
                        filter(models.BeamClass.id==int(power_class_str)).one()

                    beam_destination = self.session.query(models.BeamDestination).\
                        filter(models.BeamDestination.name==d).one()
                    fault_state.add_allowed_class(beam_class=beam_class, beam_destination=beam_destination)
        else: # if fault=='all'
          mit_location = device_info['mitigation']
          for k in mitigation[mit_location]:
            device_fault = self.getFault(faults, k)
            if (device_fault == None):
              print 'ERROR: Failed to find Fault for device "{0}"'.format(device_info['name'])
              exit(-1)
#            device_fault = models.Fault(name=mitigation[mit_location][k]['state_name'], description=device_info['device'] +
#                                        ' ' + mitigation[mit_location][k]['state_name'] + ' Fault')
            if (self.verbose):
              print '  Fault: {0} ({1}, {2})'.format(device_fault.name, mit_location, k)
              print '         device_state={0} value={1}'.format(device_states[k].name, device_states[k].value)
            self.session.add(device_fault)

            device_fault_input = models.FaultInput(bit_position=0, device=device, fault=device_fault)
            self.session.add(device_fault_input)

            for key in mitigation:
              if device_info['mitigation'] == key:
                for m in mitigation[device_info['mitigation']]:
                  if m == mitigation[mit_location][k]['state_name']:
#                    print m
                    fault_state = models.FaultState(device_state=device_states[m], fault=device_fault)
                    self.session.add(fault_state)

                    # Add the AllowedClasses for each fault state (there may be multiple per FaultState)
                    for d in self.beam_destinations:
                      power_class_str = mitigation[device_info['mitigation']][device_states[m].name][d.lower()]
                      if (power_class_str != '-'):
                        beam_class = self.session.query(models.BeamClass).\
                            filter(models.BeamClass.id==int(power_class_str)).one()

                        beam_destination = self.session.query(models.BeamDestination).\
                            filter(models.BeamDestination.name==d).one()
                        fault_state.add_allowed_class(beam_class=beam_class, beam_destination=beam_destination)


    f.close()

  #(venv)[lpiccoli@lcls-dev3 PROF]$ ll
  #
  # DeviceStates.csv
  # DeviceType.csv
  # Devices.csv
  # DigitalChannels.csv
  # Mitigation.csv
  def add_digital_device(self, directory, card_name="Digital Card"):
    print 'Adding ' + directory
    # Find the device type
    file_name = directory + '/DeviceType.csv'
    [device_type, evaluation_string, measured_device_type_id] = self.check_device_type(file_name)
    if device_type == None:
      return

    # Add DeviceStates
    file_name = directory + '/DeviceStates.csv'
    [faults, device_states] = self.add_device_states(file_name, device_type, False)

    # Add DigitalChannels, first read the channels for one device

    file_name = directory + '/DigitalChannels.csv'
    soft = False
    try:
      f = open(file_name)
    except:
      file_name = directory + '/SoftChannels.csv'
      soft=True

    if soft:
      try:
        f = open(file_name)
      except:
        print 'ERROR: No file found ({0})'.format(file_name)
        return


    line = f.readline().strip()
    fields=[]
    for field in line.split(','):
      fields.append(str(field).lower())

    channel={}
    while line:
      channel_info={}
      line = f.readline().strip()

      if line:
        field_index = 0
        for property in line.split(','):
          channel_info[fields[field_index]]=property
          field_index = field_index + 1
          
        channel[channel_info['name']]=channel_info

#    for key in channel:
#      print 'Key: {3}, Name: {0}, ZeroName: {1}, OneName: {2}, MPS Ch: {4}'.\
#          format(channel[key]['name'], channel[key]['z_name'],
#                 channel[key]['o_name'], key, channel[key]['mps_channel_#'])

    f.close()

    # Read Mitigation list
    file_name = directory + '/Mitigation.csv'
    mitigation = self.read_mitigation(file_name)

    # Read Ignore conditions (if any)
    file_name = directory + '/Conditions.csv'
    conditions = None
    if (os.path.isfile(file_name)):
      conditions = self.read_conditions(file_name)

    # Read list of devices, create Faults, FaultStates, etc...
    file_name = directory + '/Devices.csv'
    f = open(file_name)
    line = f.readline().strip()
    fields=[]
    has_measured_device=False
    for field in line.split(','):
      lower_case_field = str(field).lower()
      fields.append(lower_case_field)
      if lower_case_field ==  'measured_device_type_id':
        has_measured_device=True

    # read every device
    while line:
      device_info={}
      line = f.readline().strip()

      if line:
        field_index = 0
        for property in line.split(','):
          device_info[fields[field_index]]=property
          field_index = field_index + 1

        try:
          app_card = self.session.query(models.ApplicationCard).\
              filter(models.ApplicationCard.id==int(device_info['application_card_number'])).one()
          if app_card.name != card_name:
            print('ERROR: digital device ({0}) assigned to non-digital card ({1} at {2} slot {3})'.\
                    format(device_info['device'], app_card.name, app_card.crate.location, app_card.slot_number))
            return
        except:
          app_card = None
#          print('ERROR: Cannot find application_card with id {0}, exiting...'.format(device_info['application_card_number']))
#          return

        measured_device = measured_device_type_id
        if has_measured_device:
          if device_info['measured_device_type_id'] != '-':
            measured_device=device_info['measured_device_type_id']

        evaluation = 0
        if device_info['mitigation'] == '-':
          evaluation = 3 # this means the device has no mitigation, no device inputs
        elif evaluation_string == 'Fast':
          evaluation = 1

        if measured_device != None:
          device = models.DigitalDevice(name=device_info['device'],
                                        position=device_info['position'],
                                        z_location=device_info['linac_z'],
                                        description=device_info['device'] + ' ' + device_type.description,
                                        device_type=device_type,
                                        card=app_card,
                                        area=device_info['area'],
                                        measured_device_type_id=measured_device,
                                        evaluation=evaluation)
        else:
          device = models.DigitalDevice(name=device_info['device'],
                                        position=device_info['position'],
                                        z_location=device_info['linac_z'],
                                        description=device_info['device'] + ' ' + device_type.description,
                                        device_type=device_type,
                                        card=app_card,
                                        area=device_info['area'],
                                        evaluation=evaluation)

        if (self.verbose):
          print '  Adding device {0}'.format(device_info['device'])
        self.session.add(device)
        self.session.commit()

        if device_info['mitigation'] != '-':
          # Add the DigitalChannels and DeviceInputs for the device
          for key in channel:
            mps_channel_index = channel[key]['mps_channel_#']
#            print mps_channel_index
#            print device_info['mps_channel_#' + mps_channel_index]
            if device_info['mps_channel_#' + mps_channel_index] != '-':
              channel_number = int(device_info['mps_channel_#' + mps_channel_index])

              if (not soft):
                digital_channel = models.DigitalChannel(number=channel_number, 
                                                        name = channel[key]['name'],
                                                        z_name=channel[key]['z_name'],
                                                        o_name=channel[key]['o_name'],
                                                        alarm_state=channel[key]['alarm_state'],
                                                        card_id=app_card.id)
                self.session.add(digital_channel)
                self.session.commit()
              else:
                digital_channel = models.DigitalChannel(number=channel_number, 
                                                        name = channel[key]['name'],
                                                        z_name=channel[key]['z_name'],
                                                        o_name=channel[key]['o_name'],
                                                        alarm_state=channel[key]['alarm_state'],
                                                        card_id=app_card.id,
                                                        num_inputs=1,
                                                        monitored_pvs=device_info['mps_signal_source_location'])
                self.session.add(digital_channel)
                self.session.commit()

              device_input = models.DeviceInput(channel = digital_channel,
                                                bit_position = int(channel[key]['bit_position']),
                                                digital_device = device,
                                                fault_value = int(channel[key]['alarm_state']))
              self.session.add(device_input)
          # end for key

          # For each device - create a Fault, FaultInputs, FaultStates and the AllowedClasses
          device_fault = models.Fault(name=device_info['fault'], description=device_info['device'] + ' Fault')
          self.session.add(device_fault)

          device_fault_input = models.FaultInput(bit_position=0, device=device, fault=device_fault)
          self.session.add(device_fault_input)

          # FaultStates (given by the Mitigation.csv file), entries whose Device_Location matches the device 
          for k in mitigation:
            if self.verbose:
              print '  + Mitigation {0}'.format(k)
            if device_info['mitigation'] == k:
              for m in mitigation[device_info['mitigation']]:
                if self.verbose:
                  print '   + {0}'.format(m)
                fault_state = models.FaultState(device_state=device_states[m], fault=device_fault)
                self.session.add(fault_state)
                if (conditions != None and device_states[m].name in conditions):
                  name = device_states[m].name
  #                print '{0} : {1}'.format(device_info['device'], device_states[m].name)
                  # Create condition inputs and conditions
                  condition = models.Condition(name='{0}_{1}'.format(device_info['device'], name.upper()),
                                               description='{0} in state {1}'.format(device_info['device'], name.upper()),
                                               value=conditions[name]["value"])
                  self.session.add(condition)
                  self.session.commit()
                  self.session.refresh(condition)

                  condition_input = models.ConditionInput(bit_position=conditions[name]["bit_position"],
                                                          fault_state = fault_state, condition=condition)
                  self.session.add(condition_input)
                  self.session.commit()
                  self.session.refresh(condition_input)

                # Add the AllowedClasses for each fault state (there may be multiple per FaultState)
                for d in self.beam_destinations:
                  power_class_str = mitigation[device_info['mitigation']][device_states[m].name][d.lower()]
                  if (power_class_str != '-'):
                    beam_class = self.session.query(models.BeamClass).\
                        filter(models.BeamClass.id==int(power_class_str)).one()

                    beam_destination = self.session.query(models.BeamDestination).\
                        filter(models.BeamDestination.name==d).one()
                    fault_state.add_allowed_class(beam_class=beam_class, beam_destination=beam_destination)

    self.session.commit()
    self.session.flush()
    f.close()

  def add_analog_bypass(self, device):
    bypass = runtime.Bypass(device=device, startdate=int(time.time()), duration=0)
    self.rt_session.add(bypass)

  def add_device_input_bypass(self, device_input):
    bypass = runtime.Bypass(device_input=device_input, startdate=int(time.time()), duration=0)
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
    mpsName = MpsName(self.session)
    print 'Creating thresholds/bypass database'
    devices = self.session.query(models.Device).all()
    for d in devices:
      rt_d = runtime.Device(mpsdb_id = d.id, mpsdb_name = d.name)
      self.rt_session.add(rt_d)
      # Add thresholds - if device is analog
      analog_devices = self.session.query(models.AnalogDevice).filter(models.AnalogDevice.id==d.id).all()
      if (len(analog_devices)==1):
        self.add_runtime_thresholds(rt_d)
        self.add_analog_bypass(rt_d)

    device_inputs = self.session.query(models.DeviceInput).all()
    for di in device_inputs:
      di_pv = mpsName.getDeviceInputNameFromId(di.id)
      rt_di = runtime.DeviceInput(mpsdb_id = di.id, device_id = di.digital_device.id, pv_name = di_pv)
      self.rt_session.add(rt_di)
      self.add_device_input_bypass(rt_di)
    self.rt_session.commit()

### MAIN

parser = argparse.ArgumentParser(description='Import MPS database from .csv files')
parser.add_argument('-v', action='store_true', default=False, dest='verbose', help='Verbose output')
args = parser.parse_args()

verbose=False
if args.verbose:
  verbose=True

importer = DatabaseImporter("mps_config_imported.db", "mps_config_imported_runtime.db", verbose)

importer.add_crates('import/Crates.csv')
importer.add_app_types('import/AppTypes.csv')
importer.add_cards('import/AppCards.csv')
importer.add_device_types('import/DeviceTypes.csv')
importer.add_beam_destinations('import/BeamDestinations.csv')
importer.add_beam_classes('import/BeamClasses.csv')

# Wire scanner not yet defined
#importer.add_digital_device('import/WIRE') # Treat this one as analog or digital?

#importer.add_analog_device('import/PBLM', card_name="Generic ADC")
importer.add_digital_device('import/PROF')
#importer.add_analog_device('import/BPMS', card_name="BPM Card", add_ignore=True)
#importer.add_analog_device('import/BEND', card_name="Generic ADC")  

if (False):
  importer.add_digital_device('import/LLRF', card_name="LLRF")
  importer.add_digital_device('import/TEMP')
  importer.add_digital_device('import/BEND_STATE')
  importer.add_digital_device('import/WIRE_PARK')
  importer.add_analog_device('import/BLEN', card_name="Analog Card", add_ignore=True)
  importer.add_analog_device('import/SOLN', card_name="Generic ADC", add_ignore=True)
  importer.add_digital_device('import/VVPG')
  importer.add_digital_device('import/VVMG')
  importer.add_digital_device('import/VVFS')
  importer.add_digital_device('import/COLL')
  importer.add_digital_device('import/FLOW')
  importer.add_digital_device('import/QUAD', card_name="Virtual Card")
  importer.add_analog_device('import/TORO', card_name="Analog Card")
  importer.add_digital_device('import/BEND_SOFT', card_name="Virtual Card")
  importer.add_analog_device('import/BLM', card_name="Generic ADC")


importer.create_runtime_database()

print 'Done.'

#link_node_card = models.ApplicationCard(name="EIC Digital Card", number=100, area="GUNB",
#                                        location="MP10", type=eic_digital_app, slot_number=2, amc=2, #amc=2 -> RTM
#                                        global_id=2, description="EIC Digital Input/Output")
