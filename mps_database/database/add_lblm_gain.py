#!/usr/bin/env python
from mps_database.mps_config import MPSConfig, models
from sqlalchemy import MetaData
from mps_database.tools.mps_reader import MpsDbReader
import argparse

"""
add_lblm_gain.py

Adds the gain_bay and gain_channel for a list of LBLM waveform channels
in the mps_database if they are not added in the json channel file.
Likely only used during initial database creation as single channel additions
will include this data in the json configuration file

arguments:
  -v: verbose output
  --db: which mps_database to operate on
  --file: csv file with LBLM, Bay, and gain channel:
      bay,ch,dev
      1,0,GUNB:212:A
"""

parser = argparse.ArgumentParser(description='Add LBLM WF gain_bay and gain_channel to mps_database')
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
      devname = 'LBLM:{0}:I0_WF'.format(device_info['dev'])
      channel = session.query(models.Channel).filter(models.Channel.name==devname).all()
      if len(channel) == 1:
        print(channel[0].name)
        channel[0].gain_bay = int(device_info['bay'])
        channel[0].gain_channel = int(device_info['ch'])
      else:
        print("ERROR: Device {0} not found!".format(devname))
  session.commit()     
