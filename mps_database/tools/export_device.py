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

def to_bool(s):
    if s:
      return 1
    else:
      return 0

class ExportDevice(MpsReader):

  def __init__(self, db_file, template_path, dest_path,clean,verbose,session):
    MpsReader.__init__(self,db_file=db_file,dest_path=dest_path,template_path=template_path,clean=clean,verbose=verbose)
    self.mps_names = MpsName(session)

  def export_digital(self,app,rows,disp_macros):
    app_path = self.get_app_path(app.link_node,app.slot_number)
    if app.slot_number < 2:
      slot = 'RTM'
    else:
      slot = '{0}'.format(app.slot_number)
    for channel in app.digital_channels:
      disp_macros.append(self.get_device_input_display_macros(app,channel))
      ch = '{0}'.format(channel.number)
      device_name = channel.description.replace(':','_').replace('_',' ')[:30]
      pv = self.mps_names.getInputPvFromChannel(channel)
      r = [app.number,slot,ch,device_name,pv]
      rows.append(r)
      self.export_cn_device_input(channel,app,app_path)
      if channel.is_virtual():
        self.export_virtual(channel,app,app_path)

  def export_cn_device_input(self,channel,card,app_path):
    path = self.get_cn_path(card.link_node)
    file = "cn_device_input.template";
    rtm = True
    if channel.alarm_state:
      rtm = False
      file = "cn_device_input_fast.template";
    macros = self.get_cn_device_macros(channel,card)
    self.write_template(path,filename='device_inputs.db',template=file, macros=macros,type='central_node')
    if not channel.is_virtual():
      if rtm:
        name = self.mps_names.getInputPvFromChannel(channel)
        states = self.get_alarm_state(channel.alarm_state)
        macros = {'N':name,
                  'P':card.get_pv_name(),
                  'SHIFT':'{0}'.format(channel.number),
                  'ONAM':'{0}'.format(channel.o_name),
                  'ZNAM':'{0}'.format(channel.z_name),
                  'ZSV':'{0}'.format(states[0]),
                  'OSV':'{0}'.format(states[1])}
        self.write_template(app_path,filename='mps.db',template='digital_input.template', macros=macros,type='link_node')


  def get_cn_device_macros(self,channel,card):
    name=self.mps_names.getInputPvFromChannel(channel)
    states = self.get_alarm_state(channel.alarm_state)
    macros = { 'P':'{0}'.format(name),
               'ONAM':'{0}'.format(channel.o_name),
               'ZNAM':'{0}'.format(channel.z_name),
               'CR':'{0}'.format(card.crate.id),
               'CA':'{0}'.format(card.number),
               'CH':'{0}'.format(channel.number),
               'ID':'{0}'.format(channel.id),
               'ZSV':'{0}'.format(states[0]),
               'OSV':'{0}'.format(states[1])}
    return macros 

  def export_virtual(self,channel,card,path):
    n = channel.monitored_pvs
    mon_pv = channel.monitored_pvs
    if n.find('WIGG') > -1:
      t = n.split(':')
      del t[3:5]
      t.append(channel.name)
      n = ':'.join(t)
    states = self.get_alarm_state(channel.alarm_state)
    vmacros = {  "P":mon_pv+'_THR',
                 "R":channel.name,
                 "N":n,
                 "INPV":mon_pv,
                 "ALSTATE":str(channel.alarm_state),
                 "NALSTATE":str(to_bool(not channel.alarm_state)),
                 "ZSV":states[0],
                 "OSV":states[1],
                 "BIT":"{:02d}".format(channel.number-32).format,
                 "ZNAM":channel.z_name,
                 "ONAM":channel.o_name, 
                 "GID":"{0}".format(card.number),
                 "SCAN":".2 second"}
    dis = channel.device_input
    if len(dis) == 1:
      di = channel.device_input[0]
      if (di.digital_device.device_type.name == 'WDOG'):
        self.write_template(path,filename='mps.db',template='watchdog.template', macros=vmacros,type='link_node')
      else:
          self.write_template(path,filename='mps.db',template='virtual.template', macros=vmacros,type='link_node')
    

  def export_analog(self,app,rows,disp_macros):
    app_path = self.get_app_path(app.link_node,app.slot_number)
    self.spare_channels = list(range(0,6))
    self.gain_channels = list(range(0,4))
    self.gain_count = 0
    is_mps = False
    slot = '{0}'.format(app.slot_number)
    for channel in app.analog_channels:
      ch = '{0}'.format(channel.number)
      device = channel.analog_device
      faults = self.get_faults(device)
      dt = device.device_type.name
      device_name = self.mps_names.getDeviceName(device)
      for f in faults:
        self.write_cn_analog_byp_macros(app,channel,f)
        device_name = "{0} {1}".format(channel.analog_device.description.replace(':','_').replace('_',' '),f.name.upper())[:30]
        pv = '{0}:{1}'.format(self.mps_names.getDeviceName(channel.analog_device),f.name.upper())
        if rows is not None:
          rows.append([app.number,slot,ch,device_name,pv])
        if dt not in ['TORO','FARC']:
          self.write_lc1(app,channel,f,dt,app_path)
        self.write_thr_base(app,channel,f,dt,app_path)
        for state in f.states:
          disp_macros.append(self.get_analog_input_display_macros(app,channel,f,state))
          self.export_cn_analog_states(app,channel,f,state)
          self.write_thr(app,channel,f,state,app_path)
          if state.device_state.name == 'NO_BEAM':
            self.write_no_beam(app,channel,f,dt,app_path)
      device_name = self.mps_names.getDeviceName(device)
      if device_name.find('CBLM') > -1:
        self.write_cblm_i1(app,channel,'I1_LOSS',dt,app_path)
        self.write_rearm_template(app,channel,app_path)
        self.write_time_windows(app,channel)
      if device_name.find('CLTS') > -1:
        self.write_cblm_i1(app,channel,'I0_BACT',dt,app_path)
      if dt in ['WF']:
        self.write_rearm_template(app,channel,app_path)
      if channel.analog_device.device_type.name not in self.non_link_node_types:
        self.export_ln_analog_db(app,channel,app_path)
        is_mps = True
    if is_mps:
      for ch in self.spare_channels:
        if ch > -1:
          macros = { "P": app.get_pv_name(),
                     "CH":str(ch),
                     "CH_NAME":"Spare",
                     "CH_PVNAME":"None",
                     "CH_SPARE":"1",
                     "TYPE":"Spare"
                   }
          macros = { "P": app.get_pv_name(),
                     "CH":str(ch),
                     "CH_NAME":'Spare',
                     "CH_PVNAME":'None'}
          self.write_template(path=self.manager_path,filename='link_nodes.db',template="channel_info.template", macros=macros,type='link_node')
          macros = {"P":'{0}'.format(app.get_pv_name()),
                    "ATTR":"CH{0}".format(ch),
                    "CH":"{0}".format(ch)}
          self.write_template(app_path,filename='mps.env',template='waveform.template',macros=macros,type='link_node')
      for ch in self.gain_channels:
        if ch > -1:
          macros = {"P":'{0}'.format(app.get_pv_name()),
                    "ATTR":"CH{0}".format(ch),
                    "CH":"{0}".format(ch)}
          self.write_template(app_path,filename='mps.env',template='gain.template',macros=macros,type='link_node')         

  def get_device_input_display_macros(self,card,channel):
    name=self.mps_names.getInputPvFromChannel(channel)
    states = self.get_alarm_state(channel.alarm_state)
    if card.slot_number < 2:
      slot = 'RTM'
    else:
      slot = '{0}'.format(card.slot_number)
    macros = {}
    macros['CRATE'] = card.link_node.crate.location
    macros['SLOT'] = slot
    macros['DEVICE'] = name
    macros['CHANNEL'] = '{0}'.format(channel.number)
    macros['DEVICE_BYP'] = name
    macros['APPID'] = '{0}'.format(card.number)
    return macros

  def get_analog_input_display_macros(self,card,channel,fault,state):
    byp_name = '{0}:{1}'.format(self.mps_names.getDeviceName(channel.analog_device),fault.name)
    dev_name = '{0}:{1}'.format(self.mps_names.getDeviceName(channel.analog_device),state.device_state.name)
    if card.slot_number < 2:
      slot = 'RTM'
    else:
      slot = '{0}'.format(card.slot_number)
    macros = {}
    macros['CRATE'] = card.link_node.crate.location
    macros['SLOT'] = slot
    macros['DEVICE'] = dev_name
    macros['CHANNEL'] = '{0}'.format(channel.number)
    macros['DEVICE_BYP'] = byp_name
    macros['APPID'] = '{0}'.format(card.number)
    return macros

  def export_cn_analog_states(self,card,channel,fault,state):
    path = self.get_cn_path(card.link_node)
    P = '{0}:{1}'.format(self.mps_names.getDeviceName(channel.analog_device),state.device_state.name)
    macros = { 'P':"{0}".format(P),
               'CR':'{0}'.format(card.link_node.crate.id),
               'CA':'{0}'.format(card.number),
               'CH':'{0}'.format(channel.number),
               'ID':'{0}'.format(channel.analog_device.id),
               'MASK':'{0}'.format(state.device_state.mask) }
    self.write_template(path,filename='analog_devices.db',template='cn_analog_fault.template',macros=macros,type='central_node')

  def write_cn_analog_byp_macros(self,card,channel,fault):
    path = self.get_cn_path(card.link_node)
    name = self.mps_names.getBaseFaultName(fault)
    bypOffset = channel.analog_device.id + fault.get_integrator_index()*self.mps_names.get_device_count()
    macros = { 'P':"{0}".format(name),
               'ID':'{0}'.format(channel.analog_device.id),
               'INT':'{0}'.format(fault.get_integrator_index()),
               'BYPID':'{0}'.format(bypOffset) }
    self.write_template(path,filename='analog_devices.db',template='cn_analog_device.template',macros=macros,type='central_node')

  def write_rearm_template(self,card,channel,path):
    macros = { "P": card.get_pv_name(),
               "DEV":self.mps_names.getDeviceName(channel.analog_device),
               "BAY":'{0}'.format(self.get_bay(card,channel))
             }
    self.write_template(path,filename='mps.db',template='stream_enable.template',macros=macros,type='link_node')

  def write_time_windows(self,card,channel):
    macros = {"P":card.get_pv_name(),
              "DEV":self.mps_names.getDeviceName(channel.analog_device),
              "CH":"{0}".format(channel.number),
              "TPR":"TPR:{0}:{1}:1".format(card.area,card.location),
              "TRG":"{0}".format(channel.number+10)}
    self.write_template(path=self.manager_path,filename='link_nodes.db',template="analog_window_time.template", macros=macros,type='link_node')

  def export_ln_analog_db(self,card,channel,path):
    macros = { "P": card.get_pv_name(),
               "CH":str(channel.number),
               "CH_NAME":channel.analog_device.description,
               "CH_PVNAME":self.mps_names.getDeviceName(channel.analog_device),
               "CH_SPARE":"0",
               "TYPE":self.get_analog_type_name(channel.analog_device.device_type.name)
             }
    #self.write_template(path,filename='mps.db',template='link_node_channel_info.template',macros=macros,type='link_node')
    int0 = (channel.number * 4)
    int1 = (channel.number * 4) + 1
    macros = {"CH":"{0}".format(channel.number),
              "PROC":"1",
              "INT0":"{0}".format(int0),
              "INT1":"{0}".format(int1),
              "NC0":"{0}".format(self.__get_int_cycles(channel.analog_device,0,True)),
              "NC1":"{0}".format(self.__get_int_cycles(channel.analog_device,1,True)),
              "SC0":"{0}".format(self.__get_int_cycles(channel.analog_device,0,False)),
              "SC1":"{0}".format(self.__get_int_cycles(channel.analog_device,1,False))}
    self.write_template(path,filename='config.yaml',template='analog_settings.template',macros=macros,type='link_node')
    self.spare_channels[channel.number] = -1
    self.write_integrator_db(card,channel,path)
    self.write_waveform_db(card,channel,path)

  def write_waveform_db(self,card,channel,path):
    attribute = self.get_attr(channel)
    macros = {"P":'{0}'.format(self.mps_names.getDeviceName(channel.analog_device)),
              "ATTR":attribute,
              "CH":"{0}".format(channel.number)}
    self.write_template(path,filename='mps.env',template='waveform.template',macros=macros,type='link_node')
    if channel.analog_device.device_type.name == 'WF':
      bay = channel.analog_device.gain_bay
      cha = channel.analog_device.gain_channel
      macros = {"P":'{0}'.format(self.mps_names.getDeviceName(channel.analog_device)),
                "ATTR":attribute,
                "CH":"{0}".format(self.get_gain_number(bay,cha))}
      self.write_template(path,filename='mps.env',template='gain.template',macros=macros,type='link_node')
      self.gain_channels[self.get_gain_number(bay,cha)] = -1
    attribute = self.get_analog_type_name(channel.analog_device.device_type.name)
    macros = {"DEV":'{0}'.format(self.mps_names.getDeviceName(channel.analog_device)),
              "PORT":"bsaPort",
              "BSAKEY":"C{0}_I0".format(channel.number),
              "SECN":"I0_{0}".format(attribute)}
    self.write_template(path,filename='mps.db',template='lc2-bsa.template',macros=macros,type='link_node')
    macros = {"DEV":'{0}'.format(self.mps_names.getDeviceName(channel.analog_device)),
              "PORT":"bsssPort",
              "BSAKEY":"C{0}_I0".format(channel.number),
              "SECN":"I0_{0}".format(attribute)}
    self.write_template(path,filename='mps.db',template='bsss.template',macros=macros,type='link_node')

  def get_gain_number(self,bay,ch):
    if bay == 0:
      if ch == 0:
        return 0
      else:
        return 1
    elif bay == 1:
      if ch == 0:
        return 2
      else:
        return 3
    else:
      return None

  def __get_int_cycles(self,device,num=0,nc=False):
    if device.device_type.name not in ['BLM']:
      return 0
    else:
      if device.name.split(':')[1] not in ['CBLM']:
        return 0
      else:
        if num == 0:
          if nc:
            return self.nc_int0_cycles
          else:
            return self.sc_int0_cycles
        else:
          if nc:
            return self.nc_int1_cycles
          else:
            return self.sc_int1_cycles

  def write_ln_input_display(self,app):
    if app.slot_number < 2:
      disp_macros = []
      for channel in app.digital_channels:
        name=self.mps_names.getInputPvFromChannel(channel)
        thr_pv = ''
        vis = True
        if channel.number < 32:
          vis = False
        pv = '{0}_INPUT_RBV'.format(name)
        dis = channel.device_input
        if len(dis) == 1:
          di = channel.device_input[0]
          if di.digital_device.device_type.name == 'WDOG':
            pv = '{0}_WDOG_RBV'.format(name)
            vis = False
          else:
            pv = '{0}_INPUT_RBV'.format(name)
            if channel.number > 31:
              if name.find('WIGG') > -1:
                pv = '{0}_INPUT_RBV'.format(name)
                thr_pv = '{0}_THR'.format(name)
              else:
                pv = '{0}_INPUT_RBV'.format(channel.monitored_pvs)
                thr_pv = '{0}_THR'.format(channel.monitored_pvs)
        else:
          pv = '{0}_INPUT_RBV'.format(name)
          if channel.number > 31:
            if name.find('WIGG') > -1:
              pv = '{0}_INPUT_RBV'.format(name)
              thr_pv = '{0}_THR'.format(name)
            else:
              pv = '{0}_INPUT_RBV'.format(channel.monitored_pvs)
              thr_pv = '{0}_THR'.format(channel.monitored_pvs)
        macros = {}
        macros['CH'] = '{0}'.format(channel.number)
        macros['NAME'] = name
        macros['PV'] = pv
        macros['VIS'] = '{0}'.format(vis)
        macros['THR_PV'] = thr_pv
        disp_macros.append(macros)
      filename = '{0}thresholds/app{1}_rtm.json'.format(self.display_path,app.number)
      self.write_json_file(filename, disp_macros)


  def get_attr(self,channel):
    attr = 'MPS'
    if channel.analog_device.device_type.name == 'WF':
      attr = 'FAST'
    if self.mps_names.getBlmType(channel.analog_device) == 'CBLM':
      attr = 'FAST'
    return attr

  def write_integrator_db(self,card,channel,path):
    for integrator in range(4):
      bsa_slot = integrator*6 + channel.number
      chan = channel.number
      inpv = "{0}:ANA_BSA_DATA_{1}.RVAL".format(card.get_pv_name(),bsa_slot)
      offset = channel.analog_device.offset
      slope = channel.analog_device.slope
      if offset == 0:
        offset = 1
      macros = { "P_DEV":self.mps_names.getDeviceName(channel.analog_device),
                 "R_DEV":'I{0}_{1}'.format(integrator,self.get_analog_type_name(channel.analog_device.device_type.name)),
                 "INT":'I{0}'.format(integrator),
                 "EGU":self.get_app_units(self.mps_names.getBlmType(channel.analog_device),''),
                 "INPV":inpv,
                 "SLOPE":'{0}'.format(slope),
                 "OFFSET":'{0}'.format(channel.analog_device.offset),
                }
      self.write_template(path,filename='mps.db',template='ln_analog.template',macros=macros,type='link_node')
      if chan > 2:
        chan = chan - 3
      macros_bsa = { "P":"{0}:I{1}_{2}".format(self.mps_names.getDeviceName(channel.analog_device),integrator,self.get_analog_type_name(channel.analog_device.device_type.name)),
                     "ATTR":"I{0}_{1}".format(integrator,self.get_analog_type_name(channel.analog_device.device_type.name)),
                     "INP":"{0}:LC1_BSA_B{1}_C{2}_I{3}".format(card.get_pv_name(),self.get_bay_number(channel.number),chan,integrator),
                     "EG":"raw",
                     "HO":"0",
                     "LO":"0",
                     "PR":"0",
                     "AD":"0"}
      #if channel.analog_device.area in self.lc1_areas:
      if card.link_node.area in self.lc1_areas:
        self.write_template(path,filename='mps.db',template='bsa.template',macros=macros_bsa,type='link_node')
        
  def write_thr(self,card,channel,fault,state,path):
    bay = self.get_bay(card,channel)
    #if state.device_state.get_bit_position() > 0:
    macros = {  "P":self.mps_names.getDeviceName(channel.analog_device),
                "BAY":format(bay),
                "APP":self.get_app_type_name(channel.analog_device.device_type.name),
                "FAULT":'{0}'.format(fault.name),
                "FAULT_INDEX":self.get_fault_index(channel.analog_device.device_type.name, fault.name, channel.number),
                "DESC":fault.description[:15],
                "EGU":self.get_app_units(channel.analog_device.device_type.name,fault.name),
                "SLOPE":'{0}'.format(channel.analog_device.slope),
                "OFFSET":'{0}'.format(channel.analog_device.offset),
                "BIT_POSITION":"{0}".format(state.device_state.get_bit_position())}
    self.write_template(path,filename='mps.db',template='thr.template',macros=macros,type='link_node')

  def write_thr_base(self,card,channel,fault,device_type,path):
    bay = self.get_bay(card,channel)
    macros = {  "P":self.mps_names.getDeviceName(channel.analog_device),
                "BAY":format(bay),
                "APP":self.get_app_type_name(channel.analog_device.device_type.name),
                "FAULT":fault.name,
                "FAULT_INDEX":self.get_fault_index(channel.analog_device.device_type.name, fault.name, channel.number),
                "DESC":fault.description[:15],
                "EGU":self.get_app_units(channel.analog_device.device_type.name,fault.name),
                "SLOPE":'{0}'.format(channel.analog_device.slope),
                "OFFSET":'{0}'.format(channel.analog_device.offset)}
    self.write_template(path,filename='mps.db',template='thr_base.template',macros=macros,type='link_node')

  def write_no_beam(self,card,channel,fault,device_type,path):
    bay = self.get_bay(card,channel)
    macros = {  "P":self.mps_names.getDeviceName(channel.analog_device),
                "BAY":format(bay),
                "APP":self.get_app_type_name(channel.analog_device.device_type.name),
                "FAULT":fault.name,
                "FAULT_INDEX":self.get_fault_index(channel.analog_device.device_type.name, fault.name, channel.number),
                "DESC":fault.description[:15],
                "EGU":self.get_app_units(channel.analog_device.device_type.name,fault.name),
                "SLOPE":'{0}'.format(channel.analog_device.slope),
                "OFFSET":'{0}'.format(channel.analog_device.offset)}
    self.write_template(path,filename='mps.db',template='idl_thr.template',macros=macros,type='link_node')

  def write_lc1(self,card,channel,fault,device_type,path):
    bay = self.get_bay(card,channel)
    macros = {  "P":self.mps_names.getDeviceName(channel.analog_device),
                "BAY":format(bay),
                "APP":self.get_app_type_name(channel.analog_device.device_type.name),
                "FAULT":fault.name,
                "FAULT_INDEX":self.get_fault_index(channel.analog_device.device_type.name, fault.name, channel.number),
                "DESC":fault.description[:15],
                "EGU":self.get_app_units(channel.analog_device.device_type.name,fault.name),
                "SLOPE":'{0}'.format(channel.analog_device.slope),
                "OFFSET":'{0}'.format(channel.analog_device.offset)}
    self.write_template(path,filename='mps.db',template='lc1_thr.template',macros=macros,type='link_node')

  def write_cblm_i1(self,card,channel,fault,device_type,path):
    bay = self.get_bay(card,channel)
    macros = {  "P":self.mps_names.getDeviceName(channel.analog_device),
                "BAY":format(bay),
                "APP":self.get_app_type_name(channel.analog_device.device_type.name),
                "FAULT":fault,
                "FAULT_INDEX":self.get_fault_index(channel.analog_device.device_type.name, fault, channel.number),
                "DESC":fault,
                "EGU":self.get_app_units(channel.analog_device.device_type.name,fault),
                "SLOPE":'{0}'.format(channel.analog_device.slope),
                "OFFSET":'{0}'.format(channel.analog_device.offset)}
    self.write_template(path,filename='mps.db',template='lc1_thr.template',macros=macros,type='link_node')

  def get_bay(self,card,channel):
    if card.type.name == "MPS Analog":
      if channel.number < 3:
        return 0
      else:
        return 1
    else:
      return channel.number

  def get_alarm_state(self,state):
    if int(state) == 0:
      return ['MAJOR','NO_ALARM']
    else:
      return ['NO_ALARM','MAJOR']
      

