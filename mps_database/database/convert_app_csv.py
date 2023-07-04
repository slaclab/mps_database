#!/usr/bin/env python
import argparse
import json
"""
convert_app_csv.py

Oroginal mps_database scripts imported from a csv file output from
a Microsoft Excel spreadsheet.  This converts that csv file to the 
json format.

arguments:
  -v: verbose output
  --csv: relative path to csv file to convert
  --file: relative path to destination .json file
  "cards": [
    {
      "crate": "L2KA00-0517",
      "number": "1",
      "slot": "1",
      "type": "RTM Digital"
    }
  ]
"""

parser = argparse.ArgumentParser(description='convert csv application cards to json format')
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
while line:
  app_info = {}
  app_macros = {}
  line = f.readline().strip()
  if line:
    field_index = 0
    for property in line.split(','):
      app_info[fields[field_index]] = property
      field_index = field_index + 1
    app_macros['number'] = app_info['number']
    app_macros['slot'] = app_info['slot']
    app_macros['crate'] = app_info['crate']
    app_macros['type'] = app_info['type']
    macros.append(app_macros)
f.close()
with open(dest_file,'a') as file:
  json.dump({'cards':macros},file,sort_keys=True,indent=2)    