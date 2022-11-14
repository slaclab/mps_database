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

  def __init__(self,filename, db_file, template_path, dest_path,clean, verbose):
    MpsReader.__init__(self,db_file=db_file,dest_path=dest_path,template_path=template_path,clean=clean,verbose=verbose)
    self.verbose = verbose
    self.file_name = filename
    self.ignore0 = []
    self.ignore1 = ['YAG01B_IGNORE']
    self.ignore2 = ['YAG01B_IGNORE1']
    self.ignore3 = ['YAG01B_IGNORE2']
    self.ignore4 = ['YAG01B_IGNORE2','TDUND_IGNORE']
    self.ignore5 = ['YAG01B_IGNORE2','TDUNDB_IGNORE']
    self.bpm_text = ['X Orbit','Y Orbit','TMIT']
    self.fault = ['X','Y','TMIT']
    self.val1 = [256,65536]
    self.val2 = [512,131072]
    self.vals = [1,2,4,8,16,32,64,128,256]
    self.ac = [0,2,3,4,5,6,None,0,13]
    self.kicker_z = 107.23
    self.sxr_kick_z = 9413
    self.hxr_kick_z = 9127
    self.filename = 'logic.json'

  def export_json(self):
    with MpsDbReader(db_file) as session:
      self.write_json(session)

  def write_json(self,session):
    path = self.dest_path
    self.write_logic_json(path=self.dest_path,filename=self.filename, template_name='logic_header.template',macros={})
    f = open(self.file_name)
    line = f.readline().strip()
    fields=[]
    for field in line.split(','):
      fields.append(str(field).lower())
    while line:
      line = f.readline().strip()
      if line:
        device_info = self.get_device_info(line,fields)
        destinations = self.get_destinations(device_info)
        ic = self.get_ignore_group(device_info,session)
        ln = int(device_info['ln'])
        link_node = session.query(models.LinkNode).filter(models.LinkNode.lcls1_id == ln).one()
        skip = True
        included = True
        if device_info['dest'].lower() == 'none':
          skip = False
        if skip:
          if device_info['type'] in ['EPICS']:
            if device_info['device'].find('WIGG') > -1:
              included = False
              if device_info['device'].find('_OUT') > -1:
                self.write_header(device_info)
                self.write_ignore_conditions(ic)
                self.write_wigg_states(device_info,destinations)
            else:
              included = self.add_two_state_logic(device_info,ic,destinations)
          if device_info['type'] in ['WDOG','TEMP','FLOW','VAC','VACI','WGTEMP','BDYTEMP','ROOM','RCBR','TIME']:
            included = self.add_two_state_logic(device_info,ic,destinations)
          if device_info['type'] in ['BPMS']:
            included = self.add_bpm(device_info,ic,destinations)
          if device_info['type'] in ['SOLN','BACT']:
            included = False
            self.write_header(device_info)
            self.write_ignore_conditions(ic)
            self.add_multiple_thresholds(device_info,1,'I0_BACT',destinations,False)
          if device_info['type'] in ['BLM','PMT']:
            included = False
            self.write_header(device_info)
            self.write_ignore_conditions(ic)
            self.add_multiple_thresholds(device_info,6,'I0_LOSS',destinations,False)
            if device_info['device'].find('CBLM') > -1:
              fname = 'I1_LOSS'
              if device_info['description'].find('Beam Loss Fault') > -1:
                description = "{0} - NC Only".format(device_info['description'])
              else:
                description = "{0} Beam Loss Fault - NC ".format(device_info['description'])
              input = '{0}:{1}'.format(device_info['device'],fname)
              macros = {'DESCRIPTION':description,
                        'FNAME':fname,
                        'DTYPE':device_info['type'],
                        'INPUT1':input}
              self.write_logic_json(path=self.dest_path,filename=self.filename, template_name='one_input.template',macros=macros)
              self.write_ignore_conditions(ic)
              self.add_cblm(device_info,destinations)

          if device_info['type'] in ['KICK']:
            included = False
            self.write_header(device_info)
            self.write_ignore_conditions(ic)
            self.add_multiple_thresholds(device_info,2,'I0_BACT',destinations,True)
          if device_info['type'] in ['TORO']:
            included = False
            self.write_header(device_info)
            self.write_ignore_conditions(ic)
            self.add_multiple_thresholds(device_info,8,'CHRG',destinations,True)
          if device_info['type'] in ['WIRE']:
            included = False
            self.write_header(device_info)
            self.write_ignore_conditions(ic)
            self.add_wire_scanner(device_info,destinations)
          if device_info['type'] in ['PROF']:
            included = False
            parts = device_info['device'].split(':')
            if 'OUT_LMTSW' in parts:
              self.write_header(device_info)
              self.write_ignore_conditions(ic)
              self.write_prof_states(device_info,destinations)
          if device_info['type'] in ['STOP']:
            included = False
            parts = device_info['device'].split(':')
            if 'OUT_LMTSW' in parts:
              self.write_header(device_info)
              self.write_ignore_conditions(ic)
              self.write_stop_states(device_info,destinations)
          if device_info['type'] in ['PAL']:
            included = False
            parts = device_info['device'].split(':')
            if 'OUT_LMTSW' in parts:
              self.write_header(device_info)
              self.write_ignore_conditions(ic)
              self.write_pal_states(device_info,destinations)
          if device_info['type'] in ['MAG']:
            included = False
            parts = device_info['device'].split(':')
            if 'OFF' in parts:
              self.write_header(device_info)
              self.write_ignore_conditions(ic)
              self.write_mag_states(device_info,destinations)
          if device_info['type'] in ['VV02']:
            included = False
            parts = device_info['device'].split(':')
            if 'CLOSED' in parts:
              self.write_logic_json(path=self.dest_path,filename=self.filename, template_name='yag01b.template',macros={})
          if device_info['type'] in ['SHUT']:
            included = False
            parts = device_info['device'].split(':')
            if 'CLOSED_LMTSW' in parts:
              self.write_logic_json(path=self.dest_path,filename=self.filename, template_name='shutter.template',macros={})
      if included and skip:
        if device_info['type'] not in ['WF']:
          print('Device not included: {0} Group {1}'.format(device_info['device'],link_node.group))    
    self.write_logic_json(path=self.dest_path,filename=self.filename, template_name='logic_end.template',macros={})
    f.close()

  def get_destinations(self,device_info):
    destinations = []
    if (';' in device_info['dest']):
      destinations = device_info['dest'].split(';')
    else:
      destinations.append(device_info['dest'])
    return destinations

  def write_pal_states(self,device_info,destinations):
    self.write_logic_json(path=self.dest_path,filename=self.filename, template_name='bpm_chrg_end.template',macros={})
    states = ['Moving','Out','P1','Broken','P2','Broken','Broken','Broken']
    ac = [0,13,3,0,3,0,0,0]
    pv = ['Moving','Out','P1','Broken0','P2','Broken1','Broken2','Broken3']
    for count in range(0,8):
        dests = self.figure_out_destinations(destinations, ac[count])
        macros = {"VAL":"{0}".format(count),
                  "TEXT":states[count],
                  "PV":pv[count],
                  "LASER0":"{0}".format(dests[0]),
                  "DIAG0":"{0}".format(dests[1]),
                  "DUMPBSY0":"{0}".format(dests[2]),
                  "DUMPHXR0":"{0}".format(dests[3]),
                  "DUMPSXR0":"{0}".format(dests[4]),
                  "LESA0":"{0}".format(dests[5])}
        if count < 7:  
          self.write_logic_json(path=self.dest_path,filename=self.filename, template_name='state_line.template',macros=macros)
        else:  
          self.write_logic_json(path=self.dest_path,filename=self.filename, template_name='state_end.template',macros=macros)

  def write_prof_states(self,device_info,destinations):
    self.write_logic_json(path=self.dest_path,filename=self.filename, template_name='bpm_chrg_end.template',macros={})
    states = ['Moving','Out','In','Broken']
    ac = [0,13,3,0]
    for count in range(0,4):
        dests = self.figure_out_destinations(destinations, ac[count])
        macros = {"VAL":"{0}".format(count),
                  "TEXT":states[count],
                  "PV":states[count],
                  "LASER0":"{0}".format(dests[0]),
                  "DIAG0":"{0}".format(dests[1]),
                  "DUMPBSY0":"{0}".format(dests[2]),
                  "DUMPHXR0":"{0}".format(dests[3]),
                  "DUMPSXR0":"{0}".format(dests[4]),
                  "LESA0":"{0}".format(dests[5])}
        if count < 3:  
          self.write_logic_json(path=self.dest_path,filename=self.filename, template_name='state_line.template',macros=macros)
        else:  
          self.write_logic_json(path=self.dest_path,filename=self.filename, template_name='state_end.template',macros=macros)

  def write_stop_states(self,device_info,destinations):
    self.write_logic_json(path=self.dest_path,filename=self.filename, template_name='bpm_chrg_end.template',macros={})
    states = ['Moving','Out','In','Broken']
    ac = [0,13,0,0]
    for count in range(0,4):
        dests = self.figure_out_destinations(destinations, ac[count])
        macros = {"VAL":"{0}".format(count),
                  "TEXT":states[count],
                  "PV":states[count],
                  "LASER0":"{0}".format(dests[0]),
                  "DIAG0":"{0}".format(dests[1]),
                  "DUMPBSY0":"{0}".format(dests[2]),
                  "DUMPHXR0":"{0}".format(dests[3]),
                  "DUMPSXR0":"{0}".format(dests[4]),
                  "LESA0":"{0}".format(dests[5])}
        if count < 3:  
          self.write_logic_json(path=self.dest_path,filename=self.filename, template_name='state_line.template',macros=macros)
        else:  
          self.write_logic_json(path=self.dest_path,filename=self.filename, template_name='state_end.template',macros=macros)

  def write_wigg_states(self,device_info,destinations):
    self.write_logic_json(path=self.dest_path,filename=self.filename, template_name='bpm_chrg_end.template',macros={})
    states = ['Moving','Out','In','Broken']
    ac = [0,13,13,0]
    for count in range(0,4):
        dests = self.figure_out_destinations(destinations, ac[count])
        macros = {"VAL":"{0}".format(count),
                  "TEXT":states[count],
                  "PV":states[count],
                  "LASER0":"{0}".format(dests[0]),
                  "DIAG0":"{0}".format(dests[1]),
                  "DUMPBSY0":"{0}".format(dests[2]),
                  "DUMPHXR0":"{0}".format(dests[3]),
                  "DUMPSXR0":"{0}".format(dests[4]),
                  "LESA0":"{0}".format(dests[5])}
        if count < 3:  
          self.write_logic_json(path=self.dest_path,filename=self.filename, template_name='state_line.template',macros=macros)
        else:  
          self.write_logic_json(path=self.dest_path,filename=self.filename, template_name='state_end.template',macros=macros)

  def write_mag_states(self,device_info,destinations):
    self.write_logic_json(path=self.dest_path,filename=self.filename, template_name='bpm_chrg_end.template',macros={})
    states = ['Broken','Off','On','Broken']
    pv = ['Broken0','Off','On','Broken1']
    ac = [0,13,13,0]
    for count in range(0,4):
        dests = self.figure_out_destinations(destinations, ac[count])
        macros = {"VAL":"{0}".format(count),
                  "TEXT":states[count],
                  "PV":pv[count],
                  "LASER0":"{0}".format(dests[0]),
                  "DIAG0":"{0}".format(dests[1]),
                  "DUMPBSY0":"{0}".format(dests[2]),
                  "DUMPHXR0":"{0}".format(dests[3]),
                  "DUMPSXR0":"{0}".format(dests[4]),
                  "LESA0":"{0}".format(dests[5])}
        if count < 3:  
          self.write_logic_json(path=self.dest_path,filename=self.filename, template_name='state_line.template',macros=macros)
        else:  
          self.write_logic_json(path=self.dest_path,filename=self.filename, template_name='state_end.template',macros=macros)            

  def add_bpm(self,device_info,ic,destinations):
    for count in range(0,3):
      self.write_header(device_info,count)
      self.write_ignore_conditions(ic)
      if count < 2:
        laser0  = diag0 = dumpbsy0 = dumphxr0 = dumpsxr0 = lesa0 = 'null'
        for dest in destinations:
          if dest == 'LASER':
            laser0 = 4
          if dest == 'DIAG0':
            diag0 = 4
          if dest == 'DUMPBSY':
            dumpbsy0 = 4
          if dest == 'DUMPHXR':
            dumphxr0 = 4
          if dest == 'DUMPSXR':
            dumpsxr0 = 4
          if dest == 'LESA':
            lesa0 = 4
        macros = {'VAL1':'{0}'.format(self.val1[count]),
                  'FAULT':'{0}'.format(self.fault[count]),
                  'LASER0':"{0}".format(laser0),
                  'DIAG0':"{0}".format(diag0),
                  'DUMPBSY0':"{0}".format(dumpbsy0),
                  'DUMPHXR0':"{0}".format(dumphxr0),
                  'DUMPSXR0':"{0}".format(dumpsxr0),
                  'LESA0':"{0}".format(lesa0)}
        self.write_logic_json(path=self.dest_path,filename=self.filename, template_name='bpm_xy_states.template',macros=macros)
      else:
        self.add_multiple_thresholds(device_info,8,'TMIT',destinations,True)
    return False

  def add_wire_scanner(self,device_info,destinations):
    self.write_logic_json(path=self.dest_path,filename=self.filename, template_name='bpm_chrg_end.template',macros={})
    dests = self.figure_out_destinations(destinations, 5)
    macros = {"VAL":"{0}".format(1),
              "TEXT":"Not Ok",
              "PV":"Not Ok",
              "LASER0":"{0}".format(dests[0]),
              "DIAG0":"{0}".format(dests[1]),
              "DUMPBSY0":"{0}".format(dests[2]),
              "DUMPHXR0":"{0}".format(dests[3]),
              "DUMPSXR0":"{0}".format(dests[4]),
              "LESA0":"{0}".format(dests[5])}
    self.write_logic_json(path=self.dest_path,filename=self.filename, template_name='state_end.template',macros=macros)

  def add_cblm(self,device_info,destinations):
    self.write_logic_json(path=self.dest_path,filename=self.filename, template_name='bpm_chrg_end.template',macros={})
    text = "{0} Thr {1}".format('I1_LOSS',0)
    fa = "{0}_T{1}".format('I1_LOSS',0)
    dests = self.figure_out_destinations(destinations, 13)
    macros = {"VAL":"{0}".format(256),
              "TEXT":text,
              "PV":fa,
              "LASER0":"{0}".format(dests[0]),
              "DIAG0":"{0}".format(dests[1]),
              "DUMPBSY0":"{0}".format(dests[2]),
              "DUMPHXR0":"{0}".format(dests[3]),
              "DUMPSXR0":"{0}".format(dests[4]),
              "LESA0":"{0}".format(dests[5])}
    self.write_logic_json(path=self.dest_path,filename=self.filename, template_name='state_end.template',macros=macros)

  def add_multiple_thresholds(self,device_info,maximum,fname,destinations,no_beam=False):
    self.write_logic_json(path=self.dest_path,filename=self.filename, template_name='bpm_chrg_end.template',macros={})
    for acount in range(0,maximum):
      if self.ac[acount] is not None:
        idx = acount
        if acount > (maximum-2) and no_beam:
          text = "No Beam"
          fa = "NO_BEAM"
          idx = 7
        else:
          text = "{0} Thr {1}".format(fname,acount)
          fa = "{0}_T{1}".format(fname,acount)
        dests = self.figure_out_destinations(destinations, self.ac[idx])
        macros = {"VAL":"{0}".format(self.vals[idx]),
                  "TEXT":text,
                  "PV":fa,
                  "LASER0":"{0}".format(dests[0]),
                  "DIAG0":"{0}".format(dests[1]),
                  "DUMPBSY0":"{0}".format(dests[2]),
                  "DUMPHXR0":"{0}".format(dests[3]),
                  "DUMPSXR0":"{0}".format(dests[4]),
                  "LESA0":"{0}".format(dests[5])}
        if acount < (maximum-1):  
          self.write_logic_json(path=self.dest_path,filename=self.filename, template_name='state_line.template',macros=macros)
        else:  
          self.write_logic_json(path=self.dest_path,filename=self.filename, template_name='state_end.template',macros=macros)

  def figure_out_destinations(self,destinations,bc):
    ret = []
    for count in range(0,6):
      ret.append('null')
    for dest in destinations:
      if dest == 'LASER':
        ret[0] = bc
      if dest == 'DIAG0':
        ret[1] = bc
      if dest == 'DUMPBSY':
        ret[2] = bc
      if dest == 'DUMPHXR':
        ret[3] = bc
      if dest == 'DUMPSXR':
        ret[4] = bc
      if dest == 'LESA':
        ret[5] = bc
    return ret  
            
  def add_two_state_logic(self,device_info,ic,destinations):
    z_state = 'Is Faulted'
    o_state = 'Is Ok'
    if device_info['type'] == 'VAC':
      z_state = 'Is Not Open'
      o_state = 'Is Open'
    self.write_header(device_info)
    self.write_ignore_conditions(ic)
    laser0 = laser1 = diag0 = diag1 = dumpbsy0 = dumpbsy1 = dumphxr0 = dumphxr1 = dumpsxr0 = dumpsxr1 = lesa0 = lesa1 = 'null'
    for dest in destinations:
      if dest == 'LASER':
        laser0 = 0
        laser1 = 13
      if dest == 'DIAG0':
        diag0 = 0
        diag1 = 13
      if dest == 'DUMPBSY':
        dumpbsy0 = 0
        dumpbsy1 = 13
      if dest == 'DUMPHXR':
        dumphxr0 = 0
        dumphxr1 = 13
      if dest == 'DUMPSXR':
        dumpsxr0 = 0
        dumpsxr1 = 13
      if dest == 'LESA':
        lesa0 = 0
        lesa1 = 13
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
    self.write_logic_json(path=self.dest_path,filename=self.filename, template_name='one_input_end.template',macros=macros)
    return False   

  def write_ignore_conditions(self,ic):
    if len(ic) > 0:
      for cond in ic:
        macros = {"CONDITION":cond}
        if cond == ic[-1]:
          self.write_logic_json(path=self.dest_path,filename=self.filename, template_name='ig_condition_end.template',macros=macros)
        else:
          self.write_logic_json(path=self.dest_path,filename=self.filename, template_name='ig_condition.template',macros=macros)

  def write_header(self,device_info,count=None):
    input = device_info['device']
    num = 1
    description = device_info['description']
    if device_info['type'] in ['EPICS','VACI']:
      if device_info['device'].find('WIGG') > -1:
        fname = 'POSITION'
        num = 2
        input2 = device_info['device'].replace('_OUT','_IN')
      else:
        fname = 'STATUS'
    elif device_info['type'] == 'TEMP':
      fname = 'TEMP_PERMIT'
    elif device_info['type'] == 'FLOW':
      fname = 'FLOW_PERMIT'
    elif device_info['type'] == 'VAC':
      fname = 'POSITION'
    elif device_info['type'] == 'WDOG':
      fname = 'WDOG'
    elif device_info['type'] == 'WGTEMP':
      fname = 'WGTEMP_PERMIT'
    elif device_info['type'] == 'BDYTEMP':
      fname = 'BDYTEMP_PERMIT'
    elif device_info['type'] == 'WIRE':
      fname = 'SPEED_OK'
    elif device_info['type'] == 'ROOM':
      fname = 'ROOM_STATUS'
    elif device_info['type'] == 'RCBR':
      fname = 'RCBR_STATUS'
    elif device_info['type'] == 'TIME':
      fname = 'TIMER_STATUS'
    elif device_info['type'] in ['PROF','STOP']:
      fname = 'POSITION'
      num = 2
      t = device_info['device'].split(':')
      del t[-1]
      t.append('IN_LMTSW')
      input2 = (':').join(t)
    elif device_info['type'] == 'MAG':
      fname = 'PWR_STATUS'
      num = 2
      t = device_info['device'].split(':')
      del t[-1]
      t.append('ON')
      input2 = (':').join(t)
    elif device_info['type'] == 'PAL':
      fname = 'POSITION'
      num = 3
      t1 = device_info['device'].split(':')
      t2 = device_info['device'].split(':')
      del t1[-1]
      del t2[-1]
      t1.append('P1_LMTSW')
      input2 = (':').join(t1)
      t2.append('P2_LMTSW')
      input3 = (':').join(t2)
    elif device_info['type'] == 'BPMS':
      if count is not None:
        fname = self.fault[count]
        description = "{0} {1} Fault".format(device_info['description'],self.bpm_text[count])
        input = '{0}:{1}'.format(device_info['device'],self.fault[count])
    elif device_info['type'] in ['SOLN','BACT']:
      fname = 'I0_BACT'
      description = "{0} Fault".format(device_info['description'])
      input = '{0}:{1}'.format(device_info['device'],fname)
    elif device_info['type'] in ['BLM','PMT']:
      fname = 'I0_LOSS'
      if device_info['description'].find('Beam Loss Fault') > -1:
        description = "{0}".format(device_info['description'])
      else:
        description = "{0} Beam Loss Fault".format(device_info['description'])
      input = '{0}:{1}'.format(device_info['device'],fname)
    elif device_info['type'] in ['KICK']:
      fname = 'I0_BACT'
      description = "{0} Magnet Fault".format(device_info['description'])
      input = '{0}:{1}'.format(device_info['device'],fname)
    elif device_info['type'] in ['TORO']:
      fname = 'CHRG'
      description = "{0} Beam Charge Fault".format(device_info['description'])
      input = '{0}:{1}'.format(device_info['device'],fname)
    if num == 1:
      macros = {'DESCRIPTION':description,
                'FNAME':fname,
                'DTYPE':device_info['type'],
                'INPUT1':input}
      self.write_logic_json(path=self.dest_path,filename=self.filename, template_name='one_input.template',macros=macros)
    elif num == 2:  
      macros = {'DESCRIPTION':description,
                'FNAME':fname,
                'DTYPE':device_info['type'],
                'INPUT1':input,
                'INPUT2':input2}
      self.write_logic_json(path=self.dest_path,filename=self.filename, template_name='two_input.template',macros=macros)  
    elif num == 3:  
      macros = {'DESCRIPTION':description,
                'FNAME':fname,
                'DTYPE':device_info['type'],
                'INPUT1':input,
                'INPUT2':input2,
                'INPUT3':input3}
      self.write_logic_json(path=self.dest_path,filename=self.filename, template_name='three_input.template',macros=macros)    

  def get_ignore_group(self,device_info,session):
    ln = int(device_info['ln'])
    link_node = session.query(models.LinkNode).filter(models.LinkNode.lcls1_id == ln).one()
    ic = self.ignore0
    if int(device_info['ignore']) == 0:
      ic = self.ignore0
    if int(device_info['ignore']) > 0 and int(device_info['ignore']) < 4:
      if link_node.group in self.cn1:
        ic = self.ignore2
      if link_node.group in self.cn2:
        ic = self.ignore3
      if link_node.group in self.cn3:
        ic = self.ignore1
    if int(device_info['ignore']) == 4:
      ic = self.ignore4
    if int(device_info['ignore']) == 5:
      ic = self.ignore5
    return ic

  def get_device_info(self,line,fields):
    device_info={}
    if line:
      field_index = 0
      for property in line.split(','):
        device_info[fields[field_index]]=property
        field_index = field_index + 1
    return device_info


parser = argparse.ArgumentParser(description='Create MPS database')
parser.add_argument('-v',action='store_true',default=False,dest='verbose',help='Verbose output')
parser.add_argument('--db',metavar='database',required=True,help='mps database file')
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

filename = args.file
db_file=args.db
template_path = args.template
dest_path = args.dest

export_release = MakeLogic(filename,db_file,template_path,dest_path,clean,verbose)
export_release.export_json()
