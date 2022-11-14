#!/usr/bin/env python
from mps_database.mps_config import MPSConfig, models, runtime
from sqlalchemy import MetaData
from mps_database.tools.mps_names import MpsName
from mps_database.tools.mps_reader import MpsReader, MpsDbReader
import datetime
import argparse
import time
import yaml
import os
import sys

parser = argparse.ArgumentParser(description='Dump BPM PVs to disable App')
parser.add_argument('-v',action='store_true',default=False,dest='verbose',help='Verbose output')
parser.add_argument('--db',metavar='database',required=True,help='MPS sqlite database file')
parser.add_argument('--file',metavar='lblms',required=True,help='List of LBLMs and AOUT info')
args = parser.parse_args()

db = args.db

file_name = args.file
f = open(file_name)
line = f.readline().strip()
fields = []
for field in line.split(','):
  fields.append(str(field).lower())
with MpsDbReader(db) as session:
  while line:
    device_info = {}
    line = f.readline().strip()
    if line:
      field_index=0
      for property in line.split(','):
        device_info[fields[field_index]] = property
        field_index += 1
      devname = 'WF:LBLM:{0}'.format(device_info['dev'])
      device = session.query(models.AnalogDevice).filter(models.AnalogDevice.name==devname).all()
      if len(device) == 1:
        print(device[0].name)
        device[0].gain_bay = int(device_info['bay'])
        device[0].gain_channel = int(device_info['ch'])
      else:
        print("ERROR: Device {0} not found!".format(devname))
  session.commit()     
