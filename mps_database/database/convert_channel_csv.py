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
  "channels": [
    {
      "appid": "379",
      "auto_reset": "1",
      "monitored_pv": "SIOC:GUNB:MP02:WDOG",
      "name": "SIOC:GUNB:MP02:WDOG",
      "number": "32",
      "o_name": "IS_OK",
      "z_location": "0",
      "z_name": "IS_FAULTED"
    }
  ]
"""
parser = argparse.ArgumentParser(description='convert csv channels to json format')
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
    # This is an analog channel
    if app_info['z_name'] == '':
      # BPMs are a special case
      if 'BPMS' in app_info['device']:
        for attr in ['X','Y','TMIT']:
          app_macros['number'] = app_info['channel']
          app_macros['name'] = '{0}:{1}'.format(app_info['device'],attr)
          app_macros['z_location'] = app_info['z']
          app_macros['appid'] = app_info['appid']
          app_macros['auto_reset'] = app_info['auto_reset']
          macros.append(app_macros)
          app_macros = {}
      else:
        attr = ''
        if app_info['type'] in ['BACT','KICK','SOLN']:
          attr = 'I0_BACT'
        elif app_info['type'] == 'BLM':
          attr = 'I0_LOSS'
        elif app_info['type'] == 'WF':
          attr = 'I0_WF'
        elif app_info['type'] == 'TORO':
          attr = 'CHRG'
        else:
          print(app_info)
          print()
        app_macros['number'] = app_info['channel']
        app_macros['name'] = '{0}:{1}'.format(app_info['device'],attr)
        app_macros['z_location'] = app_info['z']
        app_macros['appid'] = app_info['appid']
        app_macros['auto_reset'] = app_info['auto_reset']
        macros.append(app_macros)
    # This is a digital channel
    else:
      if app_info['type'] in ['WDOG']:
        new_name = app_info['device'].split(':')
        new_name[-1] = 'WDOG'
        app_info['device'] = ':'.join(new_name)
      monitored_pv = ''
      if app_info['type'] in ['EPICS','WDOG']:
        monitored_pv = app_info['device']
      app_macros['number'] = app_info['channel']
      app_macros['appid'] = app_info['appid']
      app_macros['name'] = app_info['device']
      app_macros['z_location'] = app_info['z']
      app_macros['z_name'] = app_info['z_name']
      app_macros['o_name'] = app_info['o_name']
      app_macros['auto_reset'] = app_info['auto_reset']
      app_macros['monitored_pv'] = monitored_pv
      macros.append(app_macros)
f.close()
with open(dest_file,'a') as file:
  json.dump({'channels':macros},file,sort_keys=True,indent=2)    