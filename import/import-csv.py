#!/usr/bin/env python
from mps_config import MPSConfig, models
from sqlalchemy import MetaData
import argparse

class DatabaseImporter:
  conf = None # MPSConfig
  session = None
  beam_destinations = []
  verbose = False

  def __init__(self, file_name, verbose):
    self.conf = MPSConfig(file_name)
    self.conf.clear_all()
    self.session = self.conf.session
    self.session.autoflush=False
    self.verbose = verbose

  def __del__(self):
    self.session.commit()
    
  def add_crates(self, file_name):
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

        crate = models.Crate(number=crate_info['number'],
                             num_slots=crate_info['num_slots'],
                             shelf_number=int(crate_info['shelf_number']),
                             location=crate_info['location'],
                             rack=crate_info['rack'],
                             elevation=crate_info['elevation'],
                             sector=crate_info['sector'])
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
              filter(models.Crate.number==app_card_info['crate_number']).one()
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
                                          description="EIC Digital Input/Output")

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
    for field in line.split(','):
      fields.append(str(field).lower())

    while line:
      type_info={}
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
    return device_type

  def add_device_states(self, file_name, device_type):
    f = open(file_name)
    line = f.readline().strip()
    fields=[]
    for field in line.split(','):
      fields.append(str(field).lower())

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

        self.session.add(device_state)

#    print device_states
#    self.session.commit()
    f.close()
    return device_states

  def read_mitigation(self, file_name):
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

    f.close()
    return mitigation

  def add_analog_device(self, directory):
    print 'Adding ' + directory
    file_name = directory + '/DeviceType.csv'
    device_type = self.check_device_type(file_name)
    if device_type == None:
      return

    file_name = directory + '/DeviceStates.csv'
    device_states = self.add_device_states(file_name, device_type)

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
                                     description=device_info['device'] + ' ' + device_type.description,
                                     area=device_info['area'],
                                     evaluation=1)
        if (self.verbose):
          print 'Analog Channel: ' + device_info['device']

        self.session.add(device)
#        self.session.commit()

        # For each device - create a Faults, FaultInputs, FaultStates and the AllowedClasses
        if device_info['fault'] != 'all':
          device_fault = models.Fault(name=device_info['fault'], description=device_info['device'] + ' Fault')
          self.session.add(device_fault)

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
        else:
#          print "MIT: "
#          print mitigation[device_info['mitigation']]
          mit_location = device_info['mitigation']
          for k in mitigation[mit_location]:
            device_fault = models.Fault(name=mitigation[mit_location][k]['state_name'], description=device_info['device'] +
                                        ' ' + mitigation[mit_location][k]['state_name'] + ' Fault')
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
  def add_digital_device(self, directory):
    print 'Adding ' + directory
    # Find the device type
    file_name = directory + '/DeviceType.csv'
    device_type = self.check_device_type(file_name)
    if device_type == None:
      return

    # Add DeviceStates
    file_name = directory + '/DeviceStates.csv'
    device_states = self.add_device_states(file_name, device_type)

    # Add DigitalChannels, first read the channels for one device
    file_name = directory + '/DigitalChannels.csv'
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

#    for key in channel:
#      print channel[key]['name']
#      print channel[key]['o_name']

    f.close()

    # Read Mitigation list
    file_name = directory + '/Mitigation.csv'
    mitigation = self.read_mitigation(file_name)

    # Read list of devices, create Faults, FaultStates, etc...
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
        except:
          print('ERROR: Cannot find application_card with id {0}, exiting...'.format(device_info['application_card_number']))
          return

        device = models.DigitalDevice(name=device_info['device'],
                                      position=device_info['position'],
                                      description=device_info['device'] + ' ' + device_type.description,
                                      device_type=device_type,
                                      card=app_card,
                                      area=device_info['area'])

        self.session.add(device)
        self.session.commit()

        # Add the DigitalChannels and DeviceInputs for the device
        for key in channel:
          mps_channel_index = channel[key]['mps_channel_#']
          channel_number = int(device_info['mps_channel_#' + mps_channel_index])

          digital_channel = models.DigitalChannel(number=channel_number, 
                                                  name = channel[key]['name'],
                                                  z_name=channel[key]['z_name'],
                                                  o_name=channel[key]['o_name'],
                                                  alarm_state=channel[key]['alarm_state'],
                                                  card_id=app_card.id)
          self.session.add(digital_channel)
          self.session.commit()

          device_input = models.DeviceInput(channel = digital_channel,
                                            bit_position = int(channel[key]['bit_position']),
                                            digital_device = device,
                                            fault_value = int(channel[key]['alarm_state']))
          self.session.add(device_input)

        # For each device - create a Fault, FaultInputs, FaultStates and the AllowedClasses
        device_fault = models.Fault(name=device_info['fault'], description=device_info['device'] + ' Fault')
        self.session.add(device_fault)

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

    self.session.commit()
    f.close()

  def check(self):
    card = self.session.query(models.ApplicationCard).\
        filter(models.ApplicationCard.id==1).one()
#    print len(card.digital_channels)

### MAIN

parser = argparse.ArgumentParser(description='Import MPS database from .csv files')
parser.add_argument('-v', action='store_true', default=False, dest='verbose', help='Verbose output')
args = parser.parse_args()

verbose=False
if args.verbose:
  verbose=True

importer = DatabaseImporter("mps_config_imported.db", verbose)

importer.add_crates('import/Crates.csv')
importer.add_app_types('import/AppTypes.csv')
importer.add_cards('import/AppCards.csv')
importer.add_device_types('import/DeviceTypes.csv')
importer.add_beam_destinations('import/BeamDestinations.csv')
importer.add_beam_classes('import/BeamClasses.csv')

importer.add_digital_device('import/PROF')
importer.add_analog_device('import/BLEN')
importer.add_analog_device('import/SOLN')
importer.add_analog_device('import/BPMS')
importer.add_analog_device('import/BLM')

importer.check()

print 'Done.'

#link_node_card = models.ApplicationCard(name="EIC Digital Card", number=100, area="GUNB",
#                                        location="MP10", type=eic_digital_app, slot_number=2, amc=2, #amc=2 -> RTM
#                                        global_id=2, description="EIC Digital Input/Output")
