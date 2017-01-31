from mps_config import MPSConfig, models
from sqlalchemy import func
import sys
import argparse
import yaml

#
# Example:
# BPM01 analog value has three bits
# Bit 0: TMIT Fault
# Bit 1: Y Fault
# Bit 2: X Fault
# 
# Fault States:
# bpm01_t_fault state -> triggered by bit 0 -> shutter=class 0
# bpm01_y_fault state -> triggered by bit 1 -> shutter=class 0
# bpm01_x_fault state -> triggered by bit 2 -> shutter=class 0
#
# Inputs:
# All combination of the three bits, from 0 to 7.
#
# Output:
# For each combination, figure out the class for each mitigation device, if
# the device is not on the list, then say it should be ignored
#
#
#(venv)[lpiccoli@lcls-dev3 mps_database]$ cat atest.yaml
#---
#AnalogTest:
#- analog_id: 11
#  value: 0
#  mitigation:
#    - mit_id: 1
#      class_num: 3
#    - mit_id: 2
#      class_num: 3
#- analog_id: 11
#  value: 1
#  mitigation:
#    - mit_id: 1
#      class_num: 1
#    - mit_id: 2
#      class_num: 3
#
# {'AnalogTest': [{'analog_id': 11, 'mitigation': [{'mit_id': 1, 'class_num': 3},
#                                                  {'mit_id': 2, 'class_num': 3}],
#                                    'value': 0},
#                 {'analog_id': 11, 'mitigation': [{'mit_id': 1, 'class_num': 1},
#                                                  {'mit_id': 2, 'class_num': 3}],
#                                    'value': 1}]}


def generateAnalogDeviceTest(session, analog_device_id, test_analog_file):
  try:
    device = session.query(models.AnalogDevice).filter(models.AnalogDevice.id==analog_device_id).one()
  except:
    print 'ERROR: Failed to find device ' + str(analog_device_id)
    return

#  for fault in session.query(models.Fault).all():
  device_state_list=[]
  fault_state_list=[]
  bits=[]
  for input in device.fault_outputs:
    for state in input.fault.states:
      try:
        device_state = session.query(models.DeviceState).filter(models.DeviceState.id==state.device_state_id).one()
      except:
        print 'ERROR: Found invalid DeviceState listed for AnalogDevice ' + str(analog_device_id)
        return
      device_state_list.append(device_state) 
      fault_state_list.append(state)
      bits.append(0)

  analog_test={}
  items=[]

  mitigation=session.query(models.MitigationDevice).all()
  classes=session.query(models.BeamClass).all()
  highest_class=0
  for c in classes:
    if (c.number > 0):
      highest_class = c.number
  
  mit_devices={}
  tests=[]
  # Number of test configurations = 2**len(device_state_list)
  for i in range(0, 2**len(device_state_list)):

    test={}
    test['analog_id']=analog_device_id
    mit=[]
    for m in mitigation:
      mit_devices[m.id]={'name': str(m.name), 'class': highest_class, 'id':m.id}

    config={}
    config['analog']=str(i)
    mitigation_devices=[]
    for j in range(0, len(bits)):
      if (i >> j & 1 != 0):
        for ac in fault_state_list[j].allowed_classes:
          mit_devices[ac.mitigation_device_id]['class']=ac.beam_class_id
#          mit.append({'mit_id':ac.mitigation_device_id,'class_num':ac.beam_class_id,'name':'blah'})

    for m in mit_devices:
      mit.append({'mit_id':mit_devices[m]['id'],'class_num':mit_devices[m]['class'],'name':mit_devices[m]['name']})

    test['mitigation']=mit
    test['value']=i
    tests.append(test)
    config['mitigation']=mit_devices
    items.append(config)
  analog_test['AnalogTest']=tests

#  print items
  
#  analog_test['config']=items
  print analog_test  
  a = {'AnalogTest': [{'analog_id': 11, 'mitigation': [{'mit_id': 1, 'class_num': 3, 'name':'Shutter'},
                                                       {'mit_id': 2, 'class_num': 3, 'name':'AOM'}],
                       'value': 0},
                      {'analog_id': 11, 'mitigation': [{'mit_id': 1, 'class_num': 1, 'name':'Shutter'},
                                                       {'mit_id': 2, 'class_num': 3, 'name':'AOM'}],
                       'value': 1}]}

  yaml.dump(analog_test, test_analog_file, explicit_start=True)
  print device

#=== MAIN ==================================================================================

parser = argparse.ArgumentParser(description='Export EPICS template database')
parser.add_argument('database', metavar='db', type=file, nargs=1, 
                    help='database file name (e.g. mps_gun.db)')
parser.add_argument('-a', metavar='analog_device_id', type=int, nargs=1,
                    help='analog device id to be tested')
parser.add_argument('--test-analog', metavar='file', type=argparse.FileType('w'), nargs='?',
                    help='YAML file containing test pattens (e.g. analog-test.yaml)')

args = parser.parse_args()

mps = MPSConfig(args.database[0].name)
session = mps.session

if (args.test_analog and args.a):
  generateAnalogDeviceTest(session, args.a[0], args.test_analog)

session.close()

