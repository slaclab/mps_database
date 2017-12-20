#!/usr/bin/env python

from mps_config import MPSConfig, models
import socket
import sys
import os
import argparse
import time
import subprocess
from docbook import DocBook

class App:
  app=None
  was_low_bits=bytearray()
  was_high_bits=bytearray()
  is_digital=True
  session=None
  num_integrators=1
  app_type=None

  def __init__(self, app, session):
      self.app = app
      self.session = session

      if app != None:
          appType = self.session.query(models.ApplicationType).\
              filter(models.ApplicationType.id==app.type_id).one()
          self.app_type = appType

          if appType.name == 'Digital Card':
              self.is_digital = True
          else:
              self.is_digital = False
              id = app.analog_channels[0].analog_device.device_type_id
              device_type = self.session.query(models.DeviceType).\
                  filter(models.DeviceType.id==id).one()
              self.num_integrators = device_type.num_integrators
#              print appType.name + " " + str(appType.number) + " " + str(app.number)
#              print "Integrators: " + str(self.num_integrators)

          self.set_good_state()

  def get_integrator(self, value):
    if value < 0x100:
      return 0
    elif value < 0x10000:
      return 1
    elif value < 0x1000000:
      return 2
    else:
      return 3

  def get_integrator_value(self, integrator, value):
    if integrator == 0:
      return value & 0xFF
    elif integrator == 1:
      return (value >> 8) & 0xFF
    elif integrator == 2:
      return (value >> 16) & 0xFF
    else:
      return (value >> 24) & 0xFF

  def set_good_state(self):
      if self.is_digital:
          self.was_low_bits = bytearray(192*[0])
          self.was_high_bits = bytearray(192*[1])
          if self.app != None:
              self.write_digital_devices()
      else:
          self.was_low_bits = bytearray(192*[1])
          self.was_high_bits = bytearray(192*[0])

  def get_id(self):
      if self.app != None:
          return self.app.id
      else:
          return -1

  def get_name(self):
      if self.app != None:
          return self.app.name
      else:
          return 'None'

  def set_channel_value(self, channel_number, value):
      if value == 0:
          was_low = 1
          was_high = 0
      else:
          was_high = 1
          was_low = 0

      self.was_low_bits[channel_number] = was_low
      self.was_high_bits[channel_number] = was_high

  # value is has 24 or 32 bits
  # channel_number is the analog channel index (from 0 to 5)
  def set_analog_channel_value(self, channel_number, value):
      integrator_index = self.get_integrator(value) # return value from 0 to 3
      actual_value = self.get_integrator_value(integrator_index, value)
#      print "Integrator: {0}; Value: {1:X}; Full: {2:X}".format(integrator_index, actual_value, value)

      for i in range(0, 4): # loop over 4 max possible integrators 
        if i == integrator_index:
          was_high = actual_value # threshold fault for high bits
          was_low = (actual_value ^ 0xFF) # remaining bits are set low
        else:
          was_high = 0
          was_low = 0xFF

        integrator_offset = self.app_type.analog_channel_count * 8 * i
#        print "Offset={0}".format(integrator_offset)
        for bit_index in range(0, 8): # set the 8-bits for the current integrator
          was_low_bit = was_low & 1
          was_low = was_low >> 1
          self.was_low_bits[integrator_offset + bit_index] = was_low_bit

          was_high_bit = was_high & 1
          was_high = was_high >> 1
          self.was_high_bits[integrator_offset + bit_index] = was_high_bit

  def write_digital_devices(self):
      # Look for the devices, find a device_state that is not a fault_state
      # and then translate into digital_channel values
      for device in self.app.devices:
          device_type = self.session.query(models.DeviceType).\
              filter(models.DeviceType.id==device.device_type_id).one()
          inputs=[None]*len(device.inputs)
          for input in device.inputs:
              channel = self.session.query(models.DigitalChannel).\
                  filter(models.DigitalChannel.id==input.channel_id).one()
#              print 'Bit pos={0}, num={1}'.format(input.bit_position, channel.number)
              inputs[input.bit_position]=channel
          for state in device_type.states:
              fault_states = self.session.query(models.FaultState).\
                  filter(models.FaultState.device_state_id==state.id).all()
              if (len(fault_states) == 0):
#                  print '{0}={1}'.format(state.name, state.value)
#                  print len(inputs)
                  for b in range(0, len(inputs)):
                      bit_value = (state.value >> b) & 1
#                      print 'bit {0}={1}'.format(b, bit_value)
                      if bit_value == 0:
                          self.was_low_bits[inputs[b].number]=1
                          self.was_high_bits[inputs[b].number]=0
                      else:
                          self.was_low_bits[inputs[b].number]=0
                          self.was_high_bits[inputs[b].number]=1

  def get_data(self):
      was_low_bytes = bytearray([0, 0, 0, 0, 0, 0, 0, 0,
                                 0, 0, 0, 0, 0, 0, 0, 0,
                                 0, 0, 0, 0, 0, 0, 0, 0])
      was_high_bytes = bytearray([0, 0, 0, 0, 0, 0, 0, 0,
                                  0, 0, 0, 0, 0, 0, 0, 0,
                                  0, 0, 0, 0, 0, 0, 0, 0])
      byte_index = 0
      bit_shift = 0
      byte = 0

      for i in range(0, len(self.was_low_bits)):

          byte |= ((self.was_low_bits[i] & 1) << bit_shift)

          bit_shift = bit_shift + 1
          if bit_shift >= 8:
              was_low_bytes[byte_index] = byte
              bit_shift = 0
              byte = 0
              byte_index = byte_index + 1

      byte_index = 0
      bit_shift = 0
      byte = 0
      for i in range(0, len(self.was_high_bits)):

          byte |= ((self.was_high_bits[i] & 1) << bit_shift)

          bit_shift = bit_shift + 1
          if bit_shift >= 8:
              was_high_bytes[byte_index] = byte
              bit_shift = 0
              byte = 0
              byte_index = byte_index + 1
              
      return was_low_bytes + was_high_bytes

class Simulator:
  databaseFileName=""
  session=0
  update_buffer=bytearray() 
  expected_mitigation=[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
  mitigation_devices=[None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None]
  apps=[]
  device_inputs=[]
  digital_device = None
  analog_device = None
  test_value = 0
  analog_test_value = []
  analog_test_value_index = 0
  debug = 0
  highest_app_id = 0
  docbook = None
  cols=[]
  header=None
  rows=[]
  test_counter=0

  def __init__(self, dbFileName, debug, docbook):
    self.docbook = docbook
    self.databaseFileName = dbFileName
    mps = MPSConfig(args.database[0].name)
    self.session = mps.session
    self.debug = debug
    apps = self.session.query(models.ApplicationCard).\
        order_by(models.ApplicationCard.global_id.desc())
    self.highest_app_id = apps[0].global_id
    for id in range(0, self.highest_app_id + 1):
        try:
            app = self.session.query(models.ApplicationCard).\
                filter(models.ApplicationCard.global_id == id).one()
        except:
            app = None
            
        self.apps.append(App(app, self.session))

  def __del__(self):
    self.session.close()

  def set_device(self, device_id, device_type='digital'):
    if device_type == 'digital':
        self.analog_device = None
        try:
            self.digital_device = self.session.query(models.DigitalDevice).\
                filter(models.DigitalDevice.id==device_id).one()
        except:
            print 'ERROR: Failed to find digital device with id={0}'.format(device_id)
            exit(1) 
        self.test_value = 0
    else:
        self.digital_device = None
        try:
            self.analog_device = self.session.query(models.AnalogDevice).\
                filter(models.AnalogDevice.id==device_id).one()
            device_type = self.session.query(models.DeviceType).\
                filter(models.DeviceType.id==self.analog_device.device_type_id).one()
        except:
            print 'ERROR: Failed to find analog device with id={0}'.format(device_id)
            exit(1) 

        self.analog_test_value = []

        for inp in self.analog_device.fault_outputs:
            fault = self.session.query(models.Fault).\
                filter(models.Fault.id==inp.fault_id).one()
            for s in fault.states:
                try:
                    device_state = self.session.query(models.DeviceState).\
                        filter(models.DeviceState.id==s.device_state_id).one()
                except:
                    print 'ERROR: Failed to find device_state'
                    exit(1)

#                print ">>>> DeviceState: " + device_state.name
#                print '{0}={1:X}'.format(device_state.name, device_state.value)
                self.analog_test_value.append({'name':device_state.name,
                                               'value':device_state.value,
                                               'fault_state':s})

        self.analog_test_value_index = 0

    for index in range(0, len(self.apps)):
        self.apps[index].set_good_state()

    self.write_update_buffer()
    self.init_expected_mitigation()

    if device_type == 'digital':
        name = self.digital_device.name
        device_id = self.digital_device.id
    else:
        name = self.analog_device.name
        device_id = self.analog_device.id
        
    if self.docbook != None:
        self.docbook.openSection('Device {0} [id={1}]'.format(name, device_id), name)
        self.docbook.closeSection()

    if self.debug >= 1:
        sys.stdout.write('+'+60*'-'+'+\n')
        print 'Device {0}'.format(name)

    if device_type == 'digital':
        self.device_inputs=[]
        self.device_inputs=list(range(len(self.digital_device.inputs)))
        for inp in self.digital_device.inputs:
            channel = self.session.query(models.DigitalChannel).\
                filter(models.DigitalChannel.id==inp.channel_id).one()
            app_index = 0
            for index in range(0, len(self.apps)):
                if self.apps[index].get_id() == channel.card_id:
                    app_index = index
                index = index + 1

            if inp.bit_position < len(self.device_inputs):
                self.device_inputs[inp.bit_position]={'input':inp, 'app_index':app_index, 'channel':channel}
        return [self.digital_device.name, None]
    else:
        channel = self.session.query(models.AnalogChannel).\
            filter(models.AnalogChannel.id==self.analog_device.channel_id).one()
        app_index = 0
        for index in range(0, len(self.apps)):
            if self.apps[index].get_id() == channel.card_id:
                app_index = index
            index = index + 1
        self.device_inputs=[]
        self.device_inputs.append({'input':None, 'app_index':app_index, 'channel':channel})
        return [self.analog_device.name, channel.name]

  # Start the device_input possible combinations
  # @return True: continue tests, False: stop test - all combinations tested
  def set_next_state(self, device_type = 'digital'):
      self.test_counter = self.test_counter + 1

      self.cols=[{'name':'c1', 'width':'0.5*'},
                 {'name':'c2', 'width':'0.5*'}]

#      print self.digital_device
      if device_type == 'digital':
          return self.set_next_digital_state()
      else:
          return self.set_next_analog_state()

  def set_next_digital_state(self):
      if self.test_value < 2**len(self.device_inputs):

          self.rows=[]
          self.rows.append(['Device value','{:02X}\n'.format(self.test_value)])

          if self.debug >= 1:
              sys.stdout.write('Device value    : {:02X}\n'.format(self.test_value))
              sys.stdout.write('Inputs          : ')

          row_text = ''
          for d in range(0, len(self.device_inputs)):
              if (self.test_value >> d) & 1:
                  bit_value = 1
              else:
                  bit_value = 0

              self.apps[self.device_inputs[d]['app_index']].\
                  set_channel_value(self.device_inputs[d]['channel'].number, bit_value);

              text = '{0}={1:01X} '.format(self.device_inputs[d]['channel'].name, bit_value)
              row_text = row_text + text
              if self.debug >= 1:
                  sys.stdout.write(text)

          self.rows.append(['Inputs', row_text])
 
          if self.debug >=1:
              sys.stdout.write('\n')

          self.write_update_buffer()
          self.set_expected_mitigation()
          self.test_value = self.test_value + 1
          if self.test_value > 2**len(self.device_inputs):
              return False
          else:
              return True
      return False

  def set_next_analog_state(self):
      if self.analog_test_value_index >= len(self.analog_test_value):
          return False

      t = self.analog_test_value[self.analog_test_value_index]

      self.rows=[]
      self.rows.append(['Device value','{:08X}'.format(t['value'])])
      self.rows.append(['Inputs',t['name']])

      if self.debug >= 1:
          sys.stdout.write('Device value    : {:08X}\n'.format(t['value']))
          sys.stdout.write('Inputs          : ')
          sys.stdout.write('{0}\n'.format(t['name']))

      self.apps[self.device_inputs[0]['app_index']].\
          set_analog_channel_value(self.device_inputs[0]['channel'].number,
                                   self.analog_test_value[self.analog_test_value_index]['value'])


      self.write_update_buffer()
      self.set_expected_mitigation()
      self.analog_test_value_index = self.analog_test_value_index + 1
      return True

  def set_expected_mitigation(self):
      self.init_expected_mitigation()

      if self.digital_device != None:
          for fault_input in self.digital_device.fault_outputs:
              fault = self.session.query(models.Fault).filter(models.Fault.id==fault_input.fault_id).one()

          row=['Device Fault State', 'None']
          self.test_name = 'No Fault'
          for state in fault.states:
              device_state = self.session.query(models.DeviceState).\
                  filter(models.DeviceState.id==state.device_state_id).one()
              if self.test_value == device_state.value:
                  self.test_name = device_state.name
                  row=['Device Fault State', self.test_name]
                  for c in state.allowed_classes:
                      beam_class = self.session.query(models.BeamClass).\
                          filter(models.BeamClass.id==c.beam_class_id).one()
                      mitigation_device = self.session.query(models.MitigationDevice).\
                          filter(models.MitigationDevice.id==c.mitigation_device_id).one()

                      index = self.mask_to_index(mitigation_device.destination_mask)
                      self.expected_mitigation[index]=beam_class.number
          self.rows.append(row)
      else:
          self.test_name = self.analog_test_value[self.analog_test_value_index]['name']
          row=['Device Fault State', self.test_name]
          for c in self.analog_test_value[self.analog_test_value_index]['fault_state'].allowed_classes:
              beam_class = self.session.query(models.BeamClass).\
                  filter(models.BeamClass.id==c.beam_class_id).one()
              mitigation_device = self.session.query(models.MitigationDevice).\
                  filter(models.MitigationDevice.id==c.mitigation_device_id).one()
              
              index = self.mask_to_index(mitigation_device.destination_mask)
              self.expected_mitigation[index]=beam_class.number
          self.rows.append(row)

      self.show_mitigation()

  def check_mitigation(self, mitigation, device_type):
    passed = True

    row_text = ''
    if self.debug >= 1:
        sys.stdout.write('Recvd Mitigation: ')
        
    for i in range(0, len(self.mitigation_devices)):
        if self.mitigation_devices[i] != None:
            text = '{0}={1} '.format(self.mitigation_devices[i].name,
                                     mitigation[i])
            row_text = row_text + text
            if self.debug >= 1:
                sys.stdout.write(text)
                
    self.rows.append(['Recvd Mitigation', row_text])

    if self.debug >= 1:
        sys.stdout.write('\n')

    if device_type == 'digital':
        table_name = self.digital_device.name + ": " + self.test_name
        table_id = 'device.{0}.{1}'.format(self.digital_device.id, self.test_counter)
    else:
        table_name = self.analog_device.name + ' ' + str(self.analog_test_value[self.analog_test_value_index-1]['name'])
        table_id = 'device.{0}.{1}'.format(self.analog_device.id, self.test_counter)

    if self.docbook != None:
        self.docbook.table(table_name, self.cols, None, self.rows, table_id)

    if mitigation != self.expected_mitigation:
        i = 0
        for m, e in zip(mitigation, self.expected_mitigation):
            i = i + 1
            if m != e:
                passed = False
    return passed


  def get_update_buffer(self):
      return self.update_buffer

  def get_expected_mitigation(self):
      return self.expected_mitigation

  def dump_update_buffer(self):
      self.dump(self.update_buffer)

  def dump(self, buffer):
      app_counter = 0
      for i in range(0, len(buffer)):
          sys.stdout.write('{:02X} '.format(buffer[i]))
          if (i + 1) % 8 == 0:
              sys.stdout.write(' [{0:3}:{1:3}]'.format(i-7, i))
              if i == 7:
                  sys.stdout.write(' [junk]')
              elif i == 15:
                  sys.stdout.write(' [timestamp]')
              elif i == 23:
                  sys.stdout.write(' [zeroes]')
              elif i > 32 and (i - 23) % 48 == 0:
                  sys.stdout.write(' [AppId={0} {1}]'.format(app_counter, self.apps[app_counter].get_name()))
                  app_counter = app_counter + 1
              sys.stdout.write('\n')

  def mask_to_index(self, mask):
      index = 0
      while mask != 1:
          mask = mask >> 1
          index = index + 1
          if index > 16:
              return 15

      return index

  def show_mitigation(self):
      if self.debug >= 1:
          sys.stdout.write('Mitigation      : ')

      row_text = ''
      for index in range(0, len(self.mitigation_devices)):
          if self.mitigation_devices[index] != None:
              text = '{0}={1} '.format(self.mitigation_devices[index].name,
                                       self.expected_mitigation[index])
              row_text = row_text + text
              if self.debug >= 1:
                  sys.stdout.write(text)
      self.rows.append(['Mitigation',row_text])

      if self.debug >= 1:
          sys.stdout.write('\n')

  def init_expected_mitigation(self):
      beam_classes = self.session.query(models.BeamClass).\
          order_by(models.BeamClass.number.desc())
      highest_class = beam_classes[0].number

      for i in range(0, len(self.expected_mitigation)):
          self.expected_mitigation[i] = 0
      
      devices = self.session.query(models.MitigationDevice).\
          order_by(models.MitigationDevice.destination_mask.asc())
      for mit in devices:
          index = self.mask_to_index(mit.destination_mask)
          self.expected_mitigation[index] = highest_class
          self.mitigation_devices[index] = mit
      

  def write_update_buffer(self):
#    self.apps=[]
    header = bytearray([1, 2, 3, 4, 0, 0, 0, 0, # 64 bits for junk
                        0, 0, 0, 0, 0, 0, 0, 0, # 64 bits for timestamp
                        0, 0, 0, 0, 0, 0, 0, 0xAA]) # Zeroes

    update_buffer = bytearray() 
    self.update_buffer = header

    for id in range(0, self.highest_app_id + 1):
        self.update_buffer = self.update_buffer + self.apps[id].get_data()

  def get_all_devices(self):
      return self.session.query(models.DigitalDevice).all()

  def get_all_analog_devices(self):
      return self.session.query(models.AnalogDevice).all()

  def get_md5sum(self):
      cmd = "md5sum {0}".format(self.databaseFileName)
      process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
      md5sum_output, error = process.communicate()
      md5sum_tokens = md5sum_output.split()
      md5sum = md5sum_tokens[0].strip()

      return md5sum

class Tester:
  simulator = None
  sock = None
  host = None
  port = None
  debug = 0
  docbook = None
  resultRows=[]

  def __init__(self, simulator, host, port, debug, docbook):
    self.simulator = simulator
    self.host = host
    self.port = port
    self.debug = debug
    self.docbook = docbook

    # create dgram udp socket
    try:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    except socket.error:
        print 'Failed to create socket'
        sys.exit()

    if self.docbook != None:
        self.docbook.writeHeaderAuthor("Test Report")

  def __del__(self):
      if self.docbook != None:
          self.docbook.writeFooter()
          self.docbook.exportPdf()

  def get_database_info(self):
      request = bytearray(['I', 'N', 'F', 'O', '?'])
      try:
          self.sock.sendto(request, (self.host, self.port))

      except socket.error, msg:
        print 'Error Code : ' + str(msg[0]) + ' Message ' + msg[1]
        print 'Failed to send database info request message'
        sys.exit()

      try:
        database_info, addr = self.sock.recvfrom(128+64+64+64)
        source = str(database_info[0:127])
        date = str(database_info[128:191])
        user = str(database_info[192:255])
        md5sum = str(database_info[256:288])
                           
        print 'Central Node Database Info:'
        print 'Source: {0}'.format(source)
        print 'Date: {0}'.format(date)
        print 'User: {0}'.format(user)
        print 'md5sum: {0}'.format(md5sum)

        db_md5sum = self.simulator.get_md5sum()
        if (db_md5sum != md5sum):
            print 'ERROR: Mismatched database md5sum:'
            print 'Test database  : {0}'.format(md5sum)
            print 'Server database: {0}'.format(db_md5sum)
            sys.exit()

      except socket.error, msg:
        print 'Error Code : ' + str(msg[0]) + ' Message ' + msg[1]
        print 'Failed to receive database info message'
        sys.exit()

      if self.docbook != None:
          test_date = time.asctime(time.localtime(time.time()))
          self.docbook.openSection('Test Information')
          self.cols=[{'name':'c1', 'width':'0.25*'},
                     {'name':'c2', 'width':'0.75*'}]
          self.rows=[]
          self.rows.append(['Db Source',source.strip('\0')])
          self.rows.append(['Db Date', date.strip('\0')])
          self.rows.append(['Db User', user.strip('\0')])
          self.rows.append(['Db md5sum', md5sum.strip('\0')])
          self.rows.append(['Test Date', test_date])
          self.rows.append(['Central Node Host', self.host])
          self.rows.append(['Central Node Port', self.port])
          self.docbook.table('Test Information', self.cols, None, self.rows, 'info')
          self.docbook.closeSection()

  def test_all(self):
      devices = self.simulator.get_all_devices()
      for device in devices:
          self.test(device.id)

      devices = self.simulator.get_all_analog_devices()
      self.digital_device = None
      for device in devices:
          self.test(device.id, 'analog')

  def test(self, device_id, device_type='digital'):
      passed = True
      [device_name, channel_name] = self.simulator.set_device(device_id, device_type)
      self.test_counter = 0

      if self.debug >= 1:
          sys.stdout.write('+'+60*'-'+'+\n')
      
      while self.simulator.set_next_state(device_type):
          if self.debug > 2:
              self.simulator.dump_update_buffer()
          self.sendUpdate()
          if not self.receiveMitigation(device_type):
              passed = False
          if self.debug >= 1:
              sys.stdout.write('+'+60*'-'+'+\n')
      
      if passed:
          self.rows=[]
          self.rows.append(['Result','PASSED'])
          self.resultRows.append(['<link linkend=\'{0}\'>{0}</link>'.format(device_name), 'PASSED', 'green'])
          if self.docbook != None:
              self.docbook.table('Result', self.cols, None, self.rows, None, 'green')
          print '{0} PASSED'.format(device_name)
      else:
          self.rows=[]
          self.rows.append(['Result','FAILED'])
          self.resultRows.append(['<link linkend=\'{0}\'>{0}</link>'.format(device_name), 'FAILED', 'red'])
          if self.docbook != None:
              self.docbook.table('Result', self.cols, None, self.rows, None, 'red')
          print '{0} FAILED'.format(device_name)

  def sendUpdate(self):
    appdata = self.simulator.get_update_buffer()

    try:
        self.sock.sendto(appdata, (self.host, self.port))

    except socket.error, msg:
        print 'Error Code : ' + str(msg[0]) + ' Message ' + msg[1]
        sys.exit()
      
  def receiveMitigation(self, device_type):
    expectedMitigation = self.simulator.get_expected_mitigation()

    try:
        data, addr = self.sock.recvfrom(8)

    except socket.error, msg:
        print 'Error Code : ' + str(msg[0]) + ' Message ' + msg[1]
        sys.exit()

    a = bytearray(data)

    mitIndex = 0;
    mitigation = []

    for x in a:
        mitigation.append(x & 0xF)
        mitigation.append((x >> 4) & 0xF) 

    return self.simulator.check_mitigation(mitigation, device_type)

  def writeResults(self):
      if self.docbook != None:
          self.docbook.openSection('Results')
          header=[{'name':'Device', 'namest':None, 'nameend':None},
                  {'name':'Result', 'namest':None, 'nameend':None}]
          self.docbook.table('Test Results', self.cols, header, self.resultRows, 'result')
          self.docbook.closeSection()

parser = argparse.ArgumentParser(description='Send link node update to central_node_engine server')
parser.add_argument('--host', metavar='hostname', type=str, nargs=1, help='Central node hostname')
parser.add_argument('--port', metavar='size', type=int, nargs='?', help='server port (default=4356)')
parser.add_argument('--debug', metavar='debug', type=int, nargs='?', help='set debug level output (default level 0)')
parser.add_argument('--device', metavar='device', type=int, nargs='?', help='device id (default - test all digital devices)')
parser.add_argument('--analog', action="store_true", help='analog device')
parser.add_argument('--report', action="store_true", help='generate pdf report')

parser.add_argument('database', metavar='db', type=file, nargs=1,
                    help='database file name (e.g. mps_gun.db)')

args = parser.parse_args()

if args.host:
    host = args.host[0]
else:    
    host = 'lcls-dev3'

port=4356
if args.port:
    port = args.port

debug = 0
if args.debug:
    debug = args.debug

device_id = -1
if args.device:
    device_id = args.device

device_type = 'digital'
if args.analog:
    device_type = 'analog'

docbook = None
if args.report:
    report = True
    docbook = DocBook('{0}-report.xml'.format(args.database[0].name.split('.')[0]))

s = Simulator(args.database[0].name, debug, docbook)
t = Tester(s, host, port, debug, docbook)

t.get_database_info()

if device_id == -1:
    t.test_all()
else:
    t.test(device_id, device_type)

t.writeResults()

