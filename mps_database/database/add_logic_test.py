#!/usr/bin/env python
from mps_database.mps_config import MPSConfig, models, runtime
from sqlalchemy import MetaData
from mps_database.tools.mps_names import MpsName
from mps_database.database.add_digital_device import AddDigitalDevice
import argparse
import time
import yaml
import os
import sys
import json

class AddLogic:

  def __init__(self, file_name, verbose, clear_all=False):
    self.database_file_name = file_name
    self.conf = MPSConfig(file_name,verbose=verbose)
    if (clear_all):
      self.conf.clear_all()
    self.session = self.conf.session
    self.session.autoflush=False
#    self.session.autoflush=True
    self.verbose = verbose
    self.mps_names = MpsName(self.session)
    self.add_digital = AddDigitalDevice(self.session,self.conf,verbose)
    self.destination_order = ['LASER','SC_DIAG0','SC_BSYD','SC_HXR','SC_SXR','SC_LESA','LASER_HTR']

  #def __del__(self):
  #  self.session.commit()

  def add_new_device(self,data):
    device_type = self.conf.find_device_type(self.session,data['ndev'])
    device_name = self.mps_names.makeDeviceName(data['devname'],device_type.name)
    existing_devices = self.session.query(models.Device).filter(models.Device.name==device_name).all()
    if len(existing_devices) > 0:
      if len(existing_devices) == 1:
        device = existing_devices[0]
    else:
      position = device_name.split(':')[3]
      area = device_name.split(':')[2]
      channels = []
      count = 0
      for input in data['inputs']:
        ch = self.find_channel(input,data,count)
        channels.append(ch)
        count += 1
      application_card = channels[0].card
      device = self.add_digital.add_device(device_name,position,0,
                               data['description'],device_type,application_card,area,
                               0)
      count = 0
      for ch in channels:
        device_input = models.DeviceInput(channel=ch,bit_position=count,digital_device=device,fault_value=0,auto_reset=1)
        count += 1
        self.session.add(device_input)
    fault = self.add_fault(data)
    fault_input = models.FaultInput(bit_position=0,device=device,fault=fault)
    self.session.add(fault_input)
    for state_info in data['states']:
      value = state_info[0]
      state_name = state_info[1].upper().replace(' ','_')
      state_description = state_info[2]
      device_state = self.get_device_state(state_name,value,device,state_description)
      fault_state = models.FaultState(device_state=device_state,fault=fault)
      self.session.add(fault_state)
      self.add_allowed_classes(state_info,fault_state)
    for ic in data['ignore_when']:
      condition = self.find_condition(ic)
      if condition:
        #already_ics = self.session.query(models.IgnoreCondition).filter(models.IgnoreCondition.device == device).all()
      #  if len(already_ics) < 1:
         ignore_condition = models.IgnoreCondition(condition=condition,device=device)
    self.session.commit()

  def find_channel(self,input,data,count):
    ch = self.session.query(models.DigitalChannel).filter(models.DigitalChannel.name==input).one()
    return ch

  def add_allowed_classes(self,state_info,fault_state):
    index = 3 #beam classes start as third element of state_info list
    for dest in self.destination_order:
      if state_info[index] is not None:
        beam_class = self.session.query(models.BeamClass).filter(models.BeamClass.number == state_info[index]).one()
        beam_dest = self.session.query(models.BeamDestination).filter(models.BeamDestination.name==dest).one()
        fault_state.add_allowed_class(beam_class=beam_class,beam_destination=beam_dest)
      index = index + 1

  def find_condition(self,ic):
    conditions = self.session.query(models.Condition).filter(models.Condition.name == ic).all()
    if len(conditions) < 1:
      print("ERROR: Ignore Condition <{0}> not found".format(ic))
      return
    if len(conditions) > 1:
      print("ERROR: Too many ignore conditions <{0}> found".format(ic))
      return
    return conditions[0]

  def find_device(self,name,alt):
    ret_dev = self.session.query(models.Device).filter(models.Device.name==name).all()
    if len(ret_dev) <1:
      ret_device = self.session.query(models.Device).filter(models.Device.name==alt).all()
      if len(ret_device) < 1:
        print("ERROR: No device found for fault input of {0}".format(name))
        return
      if len(ret_dev) > 1:
        print("ERROR: Too many devices found for fault input of {0}".format(name))
        return
      return ret_device[0]
    if len(ret_dev) > 1:
      print("ERROR: Too many devices found for fault input of {0}".format(name))
      return
    return ret_dev[0]
    
  def add_fault(self,logic):
      existing_fault_names = self.session.query(models.Fault).filter(models.Fault.description == logic['description']).all()
      if len(existing_fault_names) > 0:
        print("ERROR: Fault {0} already exists!".format(logic['description']))
        return
      fault = models.Fault(name=logic['name'],description=logic['description'])
      self.session.add(fault)
      return fault

  def get_device_state(self,name,value,device,description):
    #First find if the device_state already exists
    #device_states = self.session.query(models.DeviceState).filter(models.DeviceState.device_type==device.device_type).all()
    #for ds in device_states:
    #  if ds.name == name.upper():
    #    if ds.value == value:
    #      return ds
    if device.discriminator=='digital_device':
      mask = 4294967295
    else:
      mask = value
    device_state = models.DeviceState(name=name.upper(),device_type=device.device_type,description=description,value=value,mask=mask)
    self.session.add(device_state)
    return device_state

  #def __del__(self):
  #  self.session.commit()

  def load_json_file(self,json_file):
    with open(json_file,'r') as session_file:
      return json.load(session_file)

parser = argparse.ArgumentParser(description='Create MPS database')
parser.add_argument('-v',action='store_true',default=False,dest='verbose',help='Verbose output')
parser.add_argument('--db',metavar='database',required=True,help='MPS sqlite database file')
parser.add_argument('--file',metavar='jsonFile',required=True,help='relative path to json file of new logic')
args = parser.parse_args()

verbose=False
if args.verbose:
  verbose=True

db_file=args.db

json_file = args.file

add_logic = AddLogic(db_file,verbose,False)
data = add_logic.load_json_file(json_file)
for logic in data['truth_tables']:
  keys = list(logic.keys())
  if 'ndev' in keys:
    add_logic.add_new_device(logic)
