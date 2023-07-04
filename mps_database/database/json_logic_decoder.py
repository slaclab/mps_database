#!/usr/bin/env python
import argparse
import json

"""
json_logic_decoder.py

Converts json logic file from old version mps_database to the format
desired with new version of mps_database.  Makes it more similar to 
lcls1 format

arguments:
  --input: relative path to previous logic json file
  --dest: relative path to new json logic file
"""

def _load_json_file(json_file):
  with open(json_file,'r') as session_file:
    return json.load(session_file)

parser = argparse.ArgumentParser(description='convert old json logic to new json format')
parser.add_argument('--input',metavar='csv',required=True,help='location of input CSV files')
parser.add_argument('--dest',metavar='destination',required=True,help='relative path to desired location of output json')
args = parser.parse_args()

inp_file = args.input
dest_file = args.dest

macros = []
inp = _load_json_file(inp_file)
for tt in inp['truth_tables']:
  out_info = {}
  out_info['name'] = tt['description']
  out_info['pv'] = tt['name']
  out_info['inputs'] = tt['inputs']
  ics = []
  for ic in tt['ignore_when']:
    ics.append(ic)
    if ic == 'YAG01B_IGNORE':
      ics.append('TEST_MODE')
    if ic == 'YAG01B_IGNORE1':
      ics.append('TEST_MODE1')
    if ic == 'YAG01B_IGNORE2':
      ics.append('TEST_MODE2')
  out_info['ignore_when'] = ics
  #print(out_info['ignore_when'])
  out_info['states'] = []
  val = 0
  for s in tt['states']:
    new_s = []
    new_s.append(val) # Value
    new_s.append(s[2]) # Name
    new_s.append(s[5]) # Mechanical Shutter (same as BSYD)
    new_s.append(s[4]) # Diag0
    new_s.append(s[5]) # BSYD
    new_s.append(s[6]) # HXR
    new_s.append(s[7]) # SXR
    new_s.append(s[8]) # LESA
    new_s.append(s[9]) # Laser Heater Shutter
    out_info['states'].append(new_s)
    val = val + 1
  macros.append(out_info)

with open(dest_file,'a') as file:
  json.dump({'truth_tables':macros},file,indent=2)    