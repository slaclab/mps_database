#!/usr/bin/env python

from mps_config import MPSConfig, models
import socket
import sys
import os
import argparse
import time

class App:
  app=None
  was_low_bits=bytearray()
  was_high_bits=bytearray()
  is_digital=True
  session=None

  def __init__(self, app, session):
      self.app = app
      self.session = session

      if app != None:
          appType = self.session.query(models.ApplicationType).\
              filter(models.ApplicationType.id==app.type_id).one()

          if appType.name == 'Digital Card':
              self.is_digital = True
          else:
              self.is_digital = False

          self.set_good_state()

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
  test_value = 0
  debug = 0
  highest_app_id = 0

  def __init__(self, dbFileName, debug):
    self.databaseFileName = dbFileName
    mps = MPSConfig(args.database[0].name)
    self.session = mps.session
    self.debug = debug
    apps = self.session.query(models.ApplicationCard).\
        order_by(models.ApplicationCard.global_id.desc())
    self.highest_app_id = apps[0].global_id

    for id in range(0, self.highest_app_id):
        try:
            app = self.session.query(models.ApplicationCard).\
                filter(models.ApplicationCard.global_id == id).one()
        except:
            app = None
            
        self.apps.append(App(app, self.session))

  def __del__(self):
    self.session.close()

  def set_device(self, device_id):
    try:
        self.digital_device = self.session.query(models.DigitalDevice).\
            filter(models.DigitalDevice.id==device_id).one()
    except:
        print 'ERROR: Failed to find digital device with id={0}'.format(device_id)
        exit(1) 

    for index in range(0, len(self.apps)):
        self.apps[index].set_good_state()

    self.write_update_buffer()
    self.init_expected_mitigation()

    if self.debug >= 1:
        sys.stdout.write('+'+60*'-'+'+\n')
        print 'Device {0}'.format(self.digital_device.name)

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

    self.test_value = 0

    return self.digital_device.name

  # Start the device_input possible combinations
  # @return True: continue tests, False: stop test - all combinations tested
  def set_next_state(self):
      if self.test_value < 2**len(self.device_inputs):
          if self.debug >= 1:
              sys.stdout.write('Device value    : {:02X}\n'.format(self.test_value))
              sys.stdout.write('Inputs          : ')

          for d in range(0, len(self.device_inputs)):
              if (self.test_value >> d) & 1:
                  bit_value = 1
              else:
                  bit_value = 0

              self.apps[self.device_inputs[d]['app_index']].\
                  set_channel_value(self.device_inputs[d]['channel'].number, bit_value);

              if self.debug >= 1:
                  sys.stdout.write('{0}={1:01X} '.format(self.device_inputs[d]['channel'].name, bit_value))
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

  def set_expected_mitigation(self):
      self.init_expected_mitigation()

      for fault_input in self.digital_device.fault_outputs:
          fault = self.session.query(models.Fault).filter(models.Fault.id==fault_input.fault_id).one()

      for state in fault.states:
          device_state = self.session.query(models.DeviceState).\
              filter(models.DeviceState.id==state.device_state_id).one()
          if self.test_value == device_state.value:
              for c in state.allowed_classes:
                  beam_class = self.session.query(models.BeamClass).\
                      filter(models.BeamClass.id==c.beam_class_id).one()
                  mitigation_device = self.session.query(models.MitigationDevice).\
                      filter(models.MitigationDevice.id==c.mitigation_device_id).one()
            
                  index = self.mask_to_index(mitigation_device.destination_mask)
                  self.expected_mitigation[index]=beam_class.number

      if self.debug >= 1:
          self.show_mitigation()

  def check_mitigation(self, mitigation):
    passed = True

    if self.debug >= 1:
        sys.stdout.write('Recvd Mitigation: ')
        for i in range(0, len(self.mitigation_devices)):
            if self.mitigation_devices[i] != None:
                sys.stdout.write('{0}={1} '.format(self.mitigation_devices[i].name,
                                                   mitigation[i]))
        sys.stdout.write('\n')


    if mitigation != self.expected_mitigation:
        i = 0
        for m, e in zip(mitigation, self.expected_mitigation):
            i = i + 1
            if m != e:
#                print "ERROR: expected power class " + str(e) + " for mitigation device #" + str(i) + ", got " + str(m) + " instead."
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
      sys.stdout.write('Mitigation      : ')

      for index in range(0, len(self.mitigation_devices)):
          if self.mitigation_devices[index] != None:
              sys.stdout.write('{0}={1} '.format(self.mitigation_devices[index].name,
                                                 self.expected_mitigation[index]))

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

    for id in range(0, self.highest_app_id):
        self.update_buffer = self.update_buffer + self.apps[id].get_data()

  def get_all_devices(self):
      return self.session.query(models.DigitalDevice).all()

class Tester:
  simulator = None
  sock = None
  host = None
  port = None
  debug = 0

  def __init__(self, simulator, host, port, debug):
    self.simulator = simulator
    self.host = host
    self.port = port
    self.debug = debug

    # create dgram udp socket
    try:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    except socket.error:
        print 'Failed to create socket'
        sys.exit()

  def test_all(self):
      devices = self.simulator.get_all_devices()
      for device in devices:
          self.test(device.id)

  def test(self, device_id):
      passed = True
      device_name = self.simulator.set_device(device_id)

      if self.debug >= 1:
          sys.stdout.write('+'+60*'-'+'+\n')

      while self.simulator.set_next_state():
          if self.debug > 2:
              self.simulator.dump_update_buffer()
          self.sendUpdate()
          if not self.receiveMitigation():
              passed = False
          if self.debug >= 1:
              sys.stdout.write('+'+60*'-'+'+\n')
      
      if passed:
          print '{0} PASSED'.format(device_name)
      else:
          print '{0} FAILED'.format(device_name)

  def sendUpdate(self):
    appdata = self.simulator.get_update_buffer()

    try:
        self.sock.sendto(appdata, (self.host, self.port))
#        print 'Update sent.'

    except socket.error, msg:
        print 'Error Code : ' + str(msg[0]) + ' Message ' + msg[1]
        sys.exit()

  def receiveMitigation(self):
    expectedMitigation = self.simulator.get_expected_mitigation()

    try:
        data, addr = self.sock.recvfrom(8)

    except socket.error, msg:
        print 'Error Code : ' + str(msg[0]) + ' Message ' + msg[1]
        sys.exit()

    a = bytearray(data)
    mitIndex = 0;
    mitigation = bytearray()
    for x in a:
        mitigation.append(x & 0xF)
        mitigation.append((x >> 4) & 0xF) 

    return self.simulator.check_mitigation(mitigation)


parser = argparse.ArgumentParser(description='Send link node update to central_node_engine server')
parser.add_argument('--host', metavar='hostname', type=str, nargs=1, help='Central node hostname')
parser.add_argument('--port', metavar='size', type=int, nargs='?', help='server port (default=4356)')
parser.add_argument('--debug', metavar='debug', type=int, nargs='?', help='set debug level output (default level 0)')
parser.add_argument('--device', metavar='device', type=int, nargs='?', help='device id (default - test all digital devices)')
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

s = Simulator(args.database[0].name, debug)
t = Tester(s, host, port, debug)

if device_id == -1:
    t.test_all()
else:
    t.test(device_id)

