#!/usr/bin/env python
import argparse
import json
"""
convert_channel_csv.py

Oroginal mps_database scripts imported from a csv file output from
a Microsoft Excel spreadsheet.  This converts that csv file to the 
json format.

arguments:
  -v: verbose output
  --csv: relative path to csv file to convert
  --file: relative path to destination .json file
  "link_nodes": [
    {
      "area": "GUNB",
      "crate": "L2KA00-0517",
      "crate_id": "1",
      "group": "0",
      "group_link": "L2KA00-1532",
      "ln_type": "2",
      "lnid": "50",
      "location": "MP01",
      "node": "SP01",
      "rx_pgp": "0"
    }
  ]
"""

parser = argparse.ArgumentParser(description='convert csv crate to json format')
parser.add_argument('--csv',metavar='csv',required=True,help='location of input CSV files')
parser.add_argument('--dest',metavar='destination',required=True,help='relative path to desired location of output json')
args = parser.parse_args()

csv_file = args.csv
dest_file = args.dest

cn1 = [8,9,10,11,12,13,14]
cn2 = [15,16,17,18,19,20,21,22,23,24]
cn3 = [0,1,2,3,4,5,6,7]

f = open(csv_file)
line = f.readline().strip()
fields = []
for field in line.split(','):
  fields.append(str(field).lower())
macros = []
old = {}
while line:
  app_info = {}
  line = f.readline().strip()
  if line:
    field_index = 0
    for property in line.split(','):
      app_info[fields[field_index]] = property
      field_index = field_index + 1
    old[app_info['column1']] = app_info

for key in old.keys():
  app_info = old[key]
  #gl = old[app_info['group_link']]
  link = app_info['group_link']
  if link == '0':
    if int(app_info['group']) in cn1:
      gl = 'B005-510'
    elif int(app_info['group']) in cn2:
      gl = 'B005-510'
    elif int(app_info['group']) in cn3:
      gl = 'L2KA00-1532'
    else:
      print("ERROR: Link to a non-existant central node")
  else:
    gl = old[link]['location']
  node = app_info['cpu_name'].split('-')[2].upper()
  app_macros = {}
  app_macros['area'] = app_info['ln_area']
  app_macros['location'] = app_info['ln_location']
  app_macros['lnid'] = app_info['lcls1_id']
  app_macros['ln_type'] = app_info['ln_type']
  app_macros['group'] = app_info['group']
  app_macros['group_link'] = gl
  app_macros['rx_pgp'] = app_info['group_link_destination']
  app_macros['crate'] = app_info['location']
  app_macros['node'] = node
  app_macros['crate_id'] = app_info['crate_id']
  macros.append(app_macros)
f.close()

with open(dest_file,'a') as file:
  json.dump({'link_nodes':macros},file,sort_keys=True,indent=2)    