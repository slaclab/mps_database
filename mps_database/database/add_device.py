#!/usr/bin/env python
from mps_database.mps_config import MPSConfig, models, runtime
from sqlalchemy import MetaData
from mps_database.tools.mps_names import MpsName
from mps_database.database.add_analog_device import AddAnalogDevice
from mps_database.database.add_digital_device import AddDigitalDevice
import argparse
import time
import yaml
import os
import sys

class AddDevice:

  def __init__(self, file_name, verbose, clear_all=False):
    self.verbose = verbose
    self.database_file_name = file_name
    self.conf = MPSConfig(file_name)
    if (clear_all):
      self.conf.clear_all()
    self.session = self.conf.session
    self.session.autoflush=False
    self.add_analog = AddAnalogDevice(self.session,self.conf,verbose)
    self.add_digital = AddDigitalDevice(self.session,self.conf,verbose)

  def __del__(self):
    self.session.commit()

  def add_device(self,file_name):
    if self.verbose:
      print(("Adding Devices... {0}".format(file_name)))
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
      if len(device_info) > 0:
        if device_info['slope'] == '':
          self.add_digital.add_digital_device(device_info)
        else:
          self.add_analog.add_analog_device(device_info)
    f.close()

parser = argparse.ArgumentParser(description='Create MPS database')
parser.add_argument('-v',action='store_true',default=False,dest='verbose',help='Verbose output')
parser.add_argument('--db',metavar='database',required=True,help='MPS sqlite database file')
parser.add_argument('--file',metavar='csvFile',required=True,help='relative path to CSV file to add')
args = parser.parse_args()

verbose=False
if args.verbose:
  verbose=True

db_file=args.db

csv_file = args.file

add_device = AddDevice(db_file,verbose,False)
add_device.add_device(csv_file)
