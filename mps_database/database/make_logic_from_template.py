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

class MakeLogic(MpsReader):

  def __init__(self, db_file, template_path, dest_path,clean, verbose):
    MpsReader.__init__(self,db_file=db_file,dest_path=dest_path,template_path=template_path,clean=clean,verbose=verbose)
    self.verbose = verbose
    self.file_name = db_file
    self.ignore0 = []
    self.ignore1 = ['YAG01B_IGNORE']
    self.ignore2 = ['YAG01B_IGNORE','VV02_IGNORE']
    self.ignore3 = ['YAG01B_IGNORE','VV02_IGNORE','COL0_IGNORE']
    self.bpm_text = ['X Orbit','Y Orbit','Charge Difference']
    self.fault = ['X','Y','CHRG']
    self.val1 = [256,65536]
    self.val2 = [512,131072]
    self.vals = [1,2,4,8,16,32,64,128]
    self.ac = [0,2,6,7,8,9,10,11]
    self.kicker_z = 107.23

  def write_json(self):
    path = self.dest_path
    self.write_logic_json(path=path,filename='logic.json', template_name='logic_header.template',macros={})
    f = open(self.file_name)
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
        ic = self.ignore0
        if int(device_info['ignore']) == 0:
          ic = self.ignore0
        if int(device_info['ignore']) == 1:
          ic = self.ignore1
        if int(device_info['ignore']) == 2:
          ic = self.ignore2
        if int(device_info['ignore']) == 3:
          ic = self.ignore3
        laser0 = laser1 = diag0 = diag1 = dumpbsy0 = dumpbsy1 = dumphxr0 = dumphxr1 = dumpsxr0 = dumpsxr1 = lesa0 = lesa1 = 'null'
        if device_info['dest'] == 'LASER':
          laser0 = 0
          laser1 = 13
        if device_info['dest'] == 'DIAG0':
          diag0 = 0
          diag1 = 13
        if device_info['dest'] == 'DUMPBSY':
          dumpbsy0 = 0
          dumpbsy1 = 13
          if float(device_info['z']) < self.kicker_z:
            diag0 = 0
            diag1 = 13
        if device_info['dest'] == 'DUMPHXR':
          dumphxr0 = 0
          dumphxr1 = 13
        if device_info['dest'] == 'DUMPSXR':
          dumpsxr0 = 0
          dumpsxr1 = 13
        if device_info['dest'] == 'LESA':
          lesa0 = 0
          lesa1 = 13
        if device_info['dest'].lower() == 'all':
          laser0 = diag0 = dumpbsy0 = dumphxr0 = dumpsxr0 = lesa0 = 0
          laser1 = diag1 = dumpbsy1 = dumphxr1 = dumpsxr1 = lesa1 = 13
        if device_info['type'] in ['WDOG','TEMP','FLOW','VAC','EPICS','VACI','WGTEMP']:
          z_state = 'Is Faulted'
          o_state = 'Is Ok'
          if device_info['type'] in ['EPICS','VACI']:
            fname = 'STATUS'
          elif device_info['type'] == 'TEMP':
            fname = 'TEMP_STATUS'
          elif device_info['type'] == 'FLOW':
            fname = 'FLOW_STATUS'
          elif device_info['type'] == 'VAC':
            fname = 'POSITION'
            z_state = 'Is Not Open'
            o_state = 'Is Open'
          elif device_info['type'] == 'WDOG':
            fname = 'WDOG'
          macros = {'DESCRIPTION':device_info['description'],
                    'FNAME':fname,
                    'DTYPE':device_info['type'],
                    'INPUT1':device_info['device']}
          self.write_logic_json(path=path,filename='logic.json', template_name='one_input.template',macros=macros)
          if len(ic) > 0:
            for cond in ic:
              macros = {"CONDITION":cond}
              if cond == ic[-1]:
                self.write_logic_json(path=path,filename='logic.json', template_name='ig_condition_end.template',macros=macros)
              else:
                self.write_logic_json(path=path,filename='logic.json', template_name='ig_condition.template',macros=macros)
          macros = {'Z_STATE':z_state,
                    'O_STATE':o_state,
                    'LASER0':"{0}".format(laser0),
                    'LASER1':"{0}".format(laser1),
                    'DIAG0':"{0}".format(diag0),
                    'DIAG1':"{0}".format(diag1),
                    'DUMPBSY0':"{0}".format(dumpbsy0),
                    'DUMPBSY1':"{0}".format(dumpbsy1),
                    'DUMPHXR0':"{0}".format(dumphxr0),
                    'DUMPHXR1':"{0}".format(dumphxr1),
                    'DUMPSXR0':"{0}".format(dumpsxr0),
                    'DUMPSXR1':"{0}".format(dumpsxr1),
                    'LESA0':"{0}".format(lesa0),
                    'LESA1':"{0}".format(lesa1)}  
          self.write_logic_json(path=path,filename='logic.json', template_name='one_input_end.template',macros=macros)              
        if device_info['type'] == 'BPMS':
          for count in range(0,3):
            description = "{0}".format(device_info['description'])
            macros = {'DESCRIPTION':description,
                      'DTYPE':'BPMS',
                      'DEVICE':device_info['device'],
                      'TEXT':self.bpm_text[count],
                      'FAULT':self.fault[count],
                      'INPUT':'{0}:{1}'.format(device_info['device'],self.fault[count])}
            self.write_logic_json(path=path,filename='logic.json', template_name='bpm_header.template',macros=macros)
            if len(ic) > 0:
              for cond in ic:
                macros = {"CONDITION":cond}
                if cond == ic[-1]:
                  self.write_logic_json(path=path,filename='logic.json', template_name='ig_condition_end.template',macros=macros)
                else:
                  self.write_logic_json(path=path,filename='logic.json', template_name='ig_condition.template',macros=macros)
            if count < 2:
              laser0 = laser1 = diag0 = diag1 = dumpbsy0 = dumpbsy1 = dumphxr0 = dumphxr1 = dumpsxr0 = dumpsxr1 = lesa0 = lesa1 = 'null'
              if device_info['dest'] == 'LASER':
                laser0 = 0
                laser1 = 4
              if device_info['dest'] == 'DIAG0':
                diag0 = 0
                diag1 = 4
              if device_info['dest'] == 'DUMPBSY':
                dumpbsy0 = 0
                dumpbsy1 = 4
                if float(device_info['z']) < self.kicker_z:
                  diag0 = 0
                  diag1 = 4
              if device_info['dest'] == 'DUMPHXR':
                dumphxr0 = 0
                dumphxr1 = 4
              if device_info['dest'] == 'DUMPSXR':
                dumpsxr0 = 0
                dumpsxr1 = 4
              if device_info['dest'] == 'LESA':
                lesa0 = 0
                lesa1 = 4
              if device_info['dest'].lower() == 'all':
                laser0 = diag0 = dumpbsy0 = dumphxr0 = dumpsxr0 = lesa0 = 0
                laser1 = diag1 = dumpbsy1 = dumphxr1 = dumpsxr1 = lesa1 = 4
              macros = {'VAL1':'{0}'.format(self.val1[count]),
                        'VAL2':'{0}'.format(self.val2[count]),
                        'FAULT':'{0}'.format(self.fault[count]),
                        'LASER0':"{0}".format(laser0),
                        'LASER1':"{0}".format(laser1),
                        'DIAG0':"{0}".format(diag0),
                        'DIAG1':"{0}".format(diag1),
                        'DUMPBSY0':"{0}".format(dumpbsy0),
                        'DUMPBSY1':"{0}".format(dumpbsy1),
                        'DUMPHXR0':"{0}".format(dumphxr0),
                        'DUMPHXR1':"{0}".format(dumphxr1),
                        'DUMPSXR0':"{0}".format(dumpsxr0),
                        'DUMPSXR1':"{0}".format(dumpsxr1),
                        'LESA0':"{0}".format(lesa0),
                        'LESA1':"{0}".format(lesa1)}  
              self.write_logic_json(path=path,filename='logic.json', template_name='bpm_xy_states.template',macros=macros)
            else:
              self.write_logic_json(path=path,filename='logic.json', template_name='bpm_chrg_end.template',macros=macros)
              for acount in range(0,8):
                laser0 = diag0 = dumpbsy0 = dumphxr0 = dumpsxr0 = lesa0 = 'null'
                if device_info['dest'] == 'LASER':
                  laser0 = self.ac[acount]
                if device_info['dest'] == 'DIAG0':
                  diag0 = self.ac[acount]
                if device_info['dest'] == 'DUMPBSY':
                  dumpbsy0 = self.ac[acount]
                  if float(device_info['z']) < self.kicker_z:
                    diag0 = self.ac[acount]
                if device_info['dest'] == 'DUMPHXR':
                  dumphxr0 = self.ac[acount]
                if device_info['dest'] == 'DUMPSXR':
                  dumpsxr0 = self.ac[acount]
                if device_info['dest'] == 'LESA':
                  lesa0 = self.ac[acount]
                if device_info['dest'].lower() == 'all':
                  laser0 = diag0 = dumpbsy0 = dumphxr0 = dumpsxr0 = lesa0 = self.ac[acount]
                macros = {"VAL":"{0}".format(self.vals[acount]),
                          "FAULT":"CHRGDIFF",
                          "TEXT":"Charge Diff",
                          "NUM":"{0}".format(acount),
                          "LASER0":"{0}".format(laser0),
                          "DIAG0":"{0}".format(diag0),
                          "DUMPBSY0":"{0}".format(dumpbsy0),
                          "DUMPHXR0":"{0}".format(dumphxr0),
                          "DUMPSXR0":"{0}".format(dumpsxr0),
                          "LESA0":"{0}".format(lesa0)}
                if acount < 7:  
                  self.write_logic_json(path=path,filename='logic.json', template_name='state_line.template',macros=macros)
                else:  
                  self.write_logic_json(path=path,filename='logic.json', template_name='state_end.template',macros=macros)
        if device_info['type'] in ['SOLN','BLM','BLEN','BACT','TORO']:
          description = "{0}".format(device_info['description'])
          if device_info['type'] in ['SOLN','BACT']:
            fault = 'I0_BACT'
            fltl = 'BACT'
          if device_info['type'] == 'BLM':
            fault = 'I0_LOSS'
            fltl = 'LOSS'
          if device_info['type'] == 'TORO':
            fault = 'CHARGE'
            fltl = 'CHARGE'
          if device_info['type'] == 'BLEN':
            fault = 'L'
            fltl = 'L'
          macros = {'DESCRIPTION':description,
                    'DTYPE':device_info['type'],
                    'DEVICE':device_info['device'],
                    'TEXT':'{0} Fault'.format(fltl.lower().title()),
                    'FAULT':fault,
                    'INPUT':'{0}:{1}'.format(device_info['device'],fault)}
          self.write_logic_json(path=path,filename='logic.json', template_name='bpm_header.template',macros=macros)
          if len(ic) > 0:
            for cond in ic:
              macros = {"CONDITION":cond}
              if cond == ic[-1]:
                self.write_logic_json(path=path,filename='logic.json', template_name='ig_condition_end.template',macros=macros)
              else:
                self.write_logic_json(path=path,filename='logic.json', template_name='ig_condition.template',macros=macros)
          self.write_logic_json(path=path,filename='logic.json', template_name='bpm_chrg_end.template',macros=macros)
          for acount in range(0,8):
            laser0 = diag0 = dumpbsy0 = dumphxr0 = dumpsxr0 = lesa0 = 'null'
            if device_info['dest'] == 'LASER':
              laser0 = self.ac[acount]
            if device_info['dest'] == 'DIAG0':
              diag0 = self.ac[acount]
            if device_info['dest'] == 'DUMPBSY':
              dumpbsy0 = self.ac[acount]
              if float(device_info['z']) < self.kicker_z:
                diag0 = self.ac[acount]
            if device_info['dest'] == 'DUMPHXR':
              dumphxr0 = self.ac[acount]
            if device_info['dest'] == 'DUMPSXR':
              dumpsxr0 = self.ac[acount]
            if device_info['dest'] == 'LESA':
              lesa0 = self.ac[acount]
            if device_info['dest'].lower() == 'all':
              laser0 = diag0 = dumpbsy0 = dumphxr0 = dumpsxr0 = lesa0 = self.ac[acount]
            macros = {"VAL":"{0}".format(self.vals[acount]),
                      "FAULT":fault,
                      "TEXT":fault,
                      "NUM":"{0}".format(acount),
                      "LASER0":"{0}".format(laser0),
                      "DIAG0":"{0}".format(diag0),
                      "DUMPBSY0":"{0}".format(dumpbsy0),
                      "DUMPHXR0":"{0}".format(dumphxr0),
                      "DUMPSXR0":"{0}".format(dumpsxr0),
                      "LESA0":"{0}".format(lesa0)}
            if acount < 7:  
              self.write_logic_json(path=path,filename='logic.json', template_name='state_line.template',macros=macros)
            else:  
              self.write_logic_json(path=path,filename='logic.json', template_name='state_end.template',macros=macros)
    self.write_logic_json(path=path,filename='logic.json', template_name='logic_end.template',macros={})
    f.close()
                           
    


parser = argparse.ArgumentParser(description='Create MPS database')
parser.add_argument('-v',action='store_true',default=False,dest='verbose',help='Verbose output')
parser.add_argument('--file',metavar='database',required=True,help='Input CSV')
parser.add_argument('--template',metavar='template',required=True,help='relative path to template files')
parser.add_argument('--dest',metavar='destination',required=True,help='relative path to desired location of output package')
parser.add_argument('-c',action='store_true',default=False,dest='clean',help='Clean export directories; default=False')
args = parser.parse_args()

clean=False
if args.clean:
  clean=True

verbose=False
if args.verbose:
  verbose=True

db_file=args.file
template_path = args.template
dest_path = args.dest

export_release = MakeLogic(db_file,template_path,dest_path,clean,verbose)
export_release.write_json()
