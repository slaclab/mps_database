#!/usr/bin/env python
from mps_database.mps_config import MPSConfig, models, runtime
from sqlalchemy import MetaData
from mps_database.tools.mps_names import MpsName
import argparse
import time
import yaml
import os
import sys
import json

class AddIgnoreDevice:

  def __init__(self, file_name, verbose, clear_all=False):
    self.database_file_name = file_name
    self.conf = MPSConfig(file_name)
    if (clear_all):
      self.conf.clear_all()
    self.session = self.conf.session
    self.session.autoflush=False
    self.verbose = verbose
    self.mps_names = MpsName(self.session)
    self.destination_order = ['LINAC','DIAG0','HXU','SXU']

  def __del__(self):
    self.session.commit()

  def add_ignore_device(self,file_name):
    if self.verbose:
      print(("Adding Ignore Logic... {0}".format(file_name)))
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
        if(self.validate_condition(device_info['name'])):
          condition = models.Condition(name=device_info['name'],description=device_info['description'],value=1)
          self.session.add(condition)
          device_name = self.mps_names.makeDeviceName(device_info['device'],device_info['type'])
          device = self.find_device(device_name,device_name)
          fault_state = self.find_fault_state(device,device_info['state'])
          if fault_state is not None:
            condition_input = models.ConditionInput(bit_position=0,fault_state=fault_state,condition=condition)
            self.session.add(condition_input)
            if self.verbose:
              print("INFO: Added Ignore Logic {0}".format(device_info['name']))
        self.session.commit()
  
  def validate_condition(self,cond):
    conditions = self.session.query(models.Condition).filter(models.Condition.description==cond).all()
    if len(conditions) > 0:
      print("ERROR: Condition {0} already exists!".format(cond))
      return False
    return True

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

  def find_fault_state(self,device,state):
    fis = self.session.query(models.FaultInput).filter(models.FaultInput.device==device).all()
    for fi in fis:
      fss = self.session.query(models.FaultState).filter(models.FaultState.fault==fi.fault).all()
      for fs in fss:
        if fs.device_state.name == state:
          return fs
    print("INFO: Fault State for ignore condition not found")
    return None

parser = argparse.ArgumentParser(description='Create MPS database')
parser.add_argument('-v',action='store_true',default=False,dest='verbose',help='Verbose output')
parser.add_argument('--db',metavar='database',required=True,help='MPS sqlite database file')
parser.add_argument('--file',metavar='csvFile',required=True,help='relative path to csv file of new Ignore Logic')
args = parser.parse_args()

verbose=False
if args.verbose:
  verbose=True

db_file=args.db

csv_file = args.file

add_ignore = AddIgnoreDevice(db_file,verbose,False)
add_ignore.add_ignore_device(csv_file)
