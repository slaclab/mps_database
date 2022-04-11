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

  def __init__(self, db_file, template_path, dest_path,clean, verbose):
    MpsReader.__init__(self,db_file=db_file,dest_path=dest_path,template_path=template_path,clean=clean,verbose=verbose)

  def export(self,mps_db_session,card,inputDisplay):
    self.inputDisplay = inputDisplay
    self.initialize_mps_names(mps_db_session)
    self.app_path = self.get_app_path(card.link_node,card.slot_number)
    if len(card.digital_channels) > 0:
      has_virtual = self.export_digital_channels(card)
      virt = 0
      if has_virtual:
        virt = 1
      self.__write_mps_virt_db(path=self.app_path, macros={"P":card.get_pv_name(),"HAS_VIRTUAL":"{0}".format(virt)})   
    elif len(card.analog_channels) > 0:
      if self.export_analog_channels(card):
        for ch in self.spare_channels:
          if ch > -1:
            macros = { "P": card.get_pv_name(),
                       "CH":str(ch),
                       "CH_NAME":"Spare",
                       "CH_PVNAME":"None",
                       "CH_SPARE":"1",
                       "TYPE":"Spare"
                     }
            self.write_link_node_channel_info_db(path=self.app_path, macros=macros)
            macros = {"P":'{0}:CH{1}_WF'.format(card.get_pv_name(),ch),
                      "CH":"{0}".format(ch)}
            self.write_epics_env(path=self.app_path, template_name='waveform.template', macros=macros)
            macros = {"P":'{0}'.format(card.get_pv_name()),
                      "CH":"{0}".format(ch),
                      "ATTR0":"I0_CH{0}".format(ch),
                      "ATTR1":"I1_CH{0}".format(ch)}
            self.write_epics_env(path=self.app_path, template_name='bsa.template', macros=macros)
  
  def export_digital_channels(self,card):
    has_virtual = False
    channels = card.digital_channels
    for channel in channels:
      self.__export_cn_device_input(channel,card)
      self.__export_device_input_display(channel,card)
      self.__write_input_report(channel,card)
      self.__write_ln_input_display(channel,card)
      if channel.monitored_pvs is not "":
        self.__export_virtual(channel,card)
        has_virtual = True
    return has_virtual   

  def export_analog_channels(self,card):
    self.spare_channels = list(range(0,6))
    is_mps = False
    json_macros = {}
    json_macros['prefix'] = card.get_pv_name()
    json_macros['cn_prefix'] = card.link_node.get_cn1_prefix()
    json_macros['devices'] = []
    json_macros['inputs'] = []
    json_macros['version_prefix'] = card.get_pv_name()
    for channel in card.analog_channels:
      json_macros = self.__export_analog_inputs(channel,card,json_macros)
      if channel.analog_device.device_type.name not in self.non_link_node_types:
        self.export_ln_analog_db(card,channel)
        is_mps = True
    filename = '{0}/App{1}_checkout.json'.format(self.checkout_path,card.number)
    self.write_json_file(filename, json_macros)
    return is_mps        

  def export_ln_analog_db(self,card,channel):
    macros = { "P": card.get_pv_name(),
               "CH":str(channel.number),
               "CH_NAME":channel.analog_device.description,
               "CH_PVNAME":self.mps_names.getDeviceName(channel.analog_device),
               "CH_SPARE":"0",
               "TYPE":self.get_analog_type_name(channel.analog_device.device_type.name)
             }
    self.write_link_node_channel_info_db(path=self.app_path, macros=macros)
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
    self.__write_ana_config(path=self.app_path, macros=macros)
    self.spare_channels[channel.number] = -1
    self.__write_integrator_db(card,channel)
    self.__write_waveform_db(card,channel)

  def __write_waveform_db(self,card,channel):
    attribute = self.get_attr(channel)
    macros = {"P":'{0}:{1}_WF'.format(self.mps_names.getDeviceName(channel.analog_device),attribute),
              "CH":"{0}".format(channel.number)}
    self.write_epics_env(path=self.app_path, template_name='waveform.template', macros=macros)
    attribute = self.get_analog_type_name(channel.analog_device.device_type.name)
    macros = {"P":'{0}'.format(self.mps_names.getDeviceName(channel.analog_device)),
              "CH":"{0}".format(channel.number),
              "ATTR0":"I0_{0}".format(attribute),
              "ATTR1":"I1_{0}".format(attribute)}
    self.write_epics_env(path=self.app_path, template_name='bsa.template', macros=macros)

  def get_attr(self,channel):
    attr = 'MPS'
    if channel.analog_device.device_type.name == 'WF':
      attr = 'FAST'
    if self.mps_names.getBlmType(channel.analog_device) == 'CBLM':
      attr = 'FAST'
    return attr

  def __write_integrator_db(self,card,channel):
    for integrator in range(4):
      bsa_slot = integrator*6 + channel.number
      chan = channel.number
      inpv = "{0}:ANA_BSA_DATA_{1}.RVAL".format(card.get_pv_name(),bsa_slot)
      offset = channel.analog_device.offset
      slope = channel.analog_device.slope
      if offset == 0:
        offset = 1
      lowerLimit = (-32768 - offset) * slope
      upperLimit = (32768 - offset) * slope
      rang = upperLimit - lowerLimit
      egul = (0-offset)*slope
      eguf = rang + egul
      macros = { "P_DEV":self.mps_names.getDeviceName(channel.analog_device),
                 "R_DEV":'I{0}_{1}'.format(integrator,self.get_analog_type_name(channel.analog_device.device_type.name)),
                 "INT":'I{0}'.format(integrator),
                 "EGU":self.get_app_units(self.mps_names.getBlmType(channel.analog_device),''),
                 "INPV":inpv,
                 "SLOPE":'{0}'.format(slope),
                 "OFFSET":'{0}'.format(channel.analog_device.offset),
                 "EGUF":'{0}'.format(eguf),
                 "EGUL":"{0}".format(egul),
                 "CH":"{0}".format(chan),
                 "P":"{0}".format(card.get_pv_name()),
                 "BAY":"{0}".format(channel.get_bay()),
                 "CH":"{0}".format(channel.number),
                 "TRG":"{0}".format(channel.number+10),
                 "AREA":card.area,
                 "LOCA":card.location,
                 "INST":"{0}".format(card.get_card_id())
                }
      self.__write_analog_db(path=self.app_path, macros=macros)
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
      if channel.analog_device.area in self.lc1_areas:
        self.__write_bsa_db(path=app_path, macros=macros_bsa)    

  def get_alarm_state(self,state):
    if int(state) == 0:
      return ['MAJOR','NO_ALARM']
    else:
      return ['NO_ALARM','MAJOR']

  def __write_input_report(self,channel,card):
    if card.slot_number < 2:
      slot = 'RTM'
    else:
      slot = '{0}'.format(card.slot_number)
    ch = '{0}'.format(channel.number)
    device_name = channel.device_input.digital_device.description.replace(':','_').replace('_',' ')[:30]
    pv = self.mps_names.getInputPvFromChannel(channel)
    appid = card.number
    self.inputDisplay.append_row([appid,slot,ch,device_name,pv])

  def __write_analog_input_report(self,channel,card,fault,state):
    if card.slot_number < 2:
      slot = 'RTM'
    else:
      slot = '{0}'.format(card.slot_number)
    ch = '{0}'.format(channel.number)
    device_name = "{0} {1}".format(channel.analog_device.description.replace(':','_').replace('_',' '),state.device_state.description)[:30]
    pv = '{0}:{1}'.format(self.mps_names.getDeviceName(channel.analog_device),state.device_state.name)
    appid = card.number
    self.inputDisplay.append_row([appid,slot,ch,device_name,pv])  

  def __write_ln_input_display(self,channel,card):
    shift = 0
    visible = False
    byte_pv = '{0}:RTM_DI'.format(card.get_pv_name())
    thr_pv = ''
    if channel.number < 32:
      shift = channel.number
    if channel.device_input.digital_device.device_type.name == 'EPICS':
      byte_pv = '{0}_INPUT_RBV'.format(channel.monitored_pvs)
      thr_pv = '{0}_THR'.format(channel.monitored_pvs)
      visible = True
    if channel.device_input.digital_device.device_type.name == 'WDOG':
      byte_pv = '{0}_WDOG_RBV'.format(channel.monitored_pvs)
    macros = {}
    macros['CH'] = '{0}'.format(channel.number)
    macros['PV'] = '{0}'.format(self.mps_names.getInputPvFromChannel(channel))
    macros['DISP_PV'] = '{0}'.format(byte_pv)
    macros['THR_PV'] = '{0}'.format(thr_pv)
    macros['SHIFT'] = '{0}'.format(shift)
    macros['VISIBLE'] = '{0}'.format(visible)
    self.inputDisplay.add_digital_ln_macros(macros)

  def __export_device_input_display(self,channel,card):
    if card.link_node.get_cn1_prefix() == 'SIOC:SYS0:MP01':
      macros = self.get_device_input_display_macros(card,channel,False)
      self.inputDisplay.add_macros(macros,False)
    elif card.link_node.get_cn1_prefix() == 'SIOC:SYS0:MP02':
      macros = self.get_device_input_display_macros(card,channel,False)
      self.inputDisplay.add_macros(macros,False)
    if card.link_node.get_cn2_prefix() == 'SIOC:SYS0:MP03':
      macros = self.get_device_input_display_macros(card,channel,True)
      self.inputDisplay.add_macros(macros,True)

  def get_device_input_display_macros(self,card,channel,exchange=False):
    name=self.mps_names.getInputPvFromChannel(channel)
    states = self.get_alarm_state(channel.alarm_state)
    if exchange:
      name = self.exchange(name)
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

  def __export_analog_inputs(self,channel,card,json_macros=None):
    faults = self.get_faults(channel.analog_device)
    self.export_threshold_display_macros(channel,card,faults)
    for fault in faults:
      if json_macros is not None:
        json_macros['devices'].append('{0}:{1}'.format(self.mps_names.getDeviceName(channel.analog_device),fault.name))
        json_macros['inputs'].append('{0}:{1}'.format(self.mps_names.getDeviceName(channel.analog_device),fault.name))
      if card.link_node.get_cn1_prefix() == 'SIOC:SYS0:MP01':
        self.write_cn_analog_byp_macros(card,channel,fault,self.cn0_path,False)
      elif card.link_node.get_cn1_prefix() == 'SIOC:SYS0:MP02':   
        self.write_cn_analog_byp_macros(card,channel,fault,self.cn1_path,False)
      if card.link_node.get_cn2_prefix() == 'SIOC:SYS0:MP03':
        self.write_cn_analog_byp_macros(card,channel,fault,self.cn2_path,True)
      self.write_thr_base_db(card,channel,fault)
      for state in fault.states:
        if card.link_node.get_cn1_prefix() == 'SIOC:SYS0:MP01':
          self.export_cn_analog_states(self.cn0_path,card,channel,fault,state,False)
          macros = self.get_analog_input_display_macros(card,channel,fault,state,False)
          self.inputDisplay.add_macros(macros,False)
        elif card.link_node.get_cn1_prefix() == 'SIOC:SYS0:MP02':
          self.export_cn_analog_states(self.cn1_path,card,channel,fault,state,False)
          macros = self.get_analog_input_display_macros(card,channel,fault,state,False)
          self.inputDisplay.add_macros(macros,False)
        if card.link_node.get_cn2_prefix() == 'SIOC:SYS0:MP03':
          self.export_cn_analog_states(self.cn2_path,card,channel,fault,state,True)
          macros = self.get_analog_input_display_macros(card,channel,fault,state,True)
          self.inputDisplay.add_macros(macros,True)
        self.__write_analog_input_report(channel,card,fault,state)
        self.write_thr(channel,card,fault,state)
    return json_macros

  def write_thr(self,channel,card,fault,state):
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
    self.__write_thr_db(path=self.app_path, macros=macros)
        
  def write_thr_base_db(self,card,channel,fault):
    inpv = None
    if channel.analog_device.area in self.hard_areas:
      inpv = 'BEND:DMPH:400:BACT'
      bpm = 'BPMS:LTUH:960:TMITCUH1H'
      name = 'DUMP:LTUH:970:MPSPOWER'
      rate = "IOC:BSY0:MP01:BYKIK_RATEC"
    if channel.analog_device.area in self.soft_areas:
      inpv = 'BEND:DMPS:400:BACT'
      bpm = 'BPMS:LTUS:880:TMITCUH1H'
      name = 'DUMP:LTUS:972:MPSPOWER'
      rate = "IOC:BSY0:MP01:BYKIKS_RATEC"
    if inpv is not None:
      if channel.analog_device.device_type.name in ['BEND']:
        macros = {"P":self.mps_names.getDeviceName(channel.analog_device),
                  "DESC":channel.analog_device.description,
                  "INPV":inpv}
        self.__write_lc1_db_db(path=self.app_path,macros=macros)
      if channel.analog_device.device_type.name in ['KICK'] and channel.analog_device.area not in ['CLTS']:
        macros_temp = { "P":self.mps_names.getDeviceName(channel.analog_device),
                        "DESC":channel.analog_device.description,
                        "INPV":inpv,
                        "BPM":bpm,
                        "NAME":name,
                        "RATE":rate} 
        self.__write_lc1_kick_db(path=self.app_path, macros=macros)
    bay = self.get_bay(card,channel)
    macros = {  "P":self.mps_names.getDeviceName(channel.analog_device),
                "BAY":format(bay),
                "APP":self.get_app_type_name(channel.analog_device.device_type.name),
                "FAULT":'{0}'.format(fault.name),
                "FAULT_INDEX":self.get_fault_index(channel.analog_device.device_type.name, fault.name, channel.number),
                "DESC":fault.description[:15],
                "EGU":self.get_app_units(channel.analog_device.device_type.name,fault.name),
                "SLOPE":'{0}'.format(channel.analog_device.slope),
                "OFFSET":'{0}'.format(channel.analog_device.offset)}
    self.__write_thr_base_db(path=self.app_path, macros=macros)
        

  def export_threshold_display_macros(self,channel,card,faults):
    macros = {}
    macros['P'] = '{0}'.format(card.get_pv_name())
    macros['CH'] = '{0}'.format(channel.number)
    macros['DEVICE_NAME'] = '{0}'.format(self.mps_names.getDeviceName(channel.analog_device))
    macros['PV_PREFIX'] = '{0}'.format(self.mps_names.getDeviceName(channel.analog_device))
    macros['THR0_P'] = False
    macros['THR1_P'] = False
    macros['THR2_P'] = False
    idx = 0
    for fault in faults:
      new_key = 'THR{0}'.format(int(idx))
      new_vis_key = 'THR{0}_P'.format(int(idx))
      macros[new_key] = fault.name
      macros[new_vis_key] = True
      idx += 1
    bay = self.get_bay(card,channel)
    self.inputDisplay.add_analog_macros(macros,bay)

  def get_bay(self,card,channel):
    if card.type.name == "MPS Analog":
      if channel.number < 3:
        return 0
      else:
        return 1
    else:
      return channel.number

  def get_analog_input_display_macros(self,card,channel,fault,state,exchange=False):
    byp_name = '{0}:{1}'.format(self.mps_names.getDeviceName(channel.analog_device),fault.name)
    dev_name = '{0}:{1}'.format(self.mps_names.getDeviceName(channel.analog_device),state.device_state.name)
    if exchange:
      byp_name = self.exchange(byp_name)
      dev_name = self.exchange(dev_name)
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

  def write_cn_analog_byp_macros(self,card,channel,fault,path,exchange=False):
    name = '{0}:{1}'.format(self.mps_names.getDeviceName(channel.analog_device),fault.name)
    if exchange:
      name = self.exchange(name)
    macros = { 'P':"{0}".format(name),
               'ID':'{0}'.format(channel.analog_device.id),
               'INT':'{0}'.format(fault.get_integrator_index()) }
    self.write_epics_db(path=path,filename='analog_devices.db', template_name="cn_analog_device.template", macros=macros)

  def export_cn_analog_states(self,path,card,channel,fault,state,exchange):
    P = '{0}:{1}'.format(self.mps_names.getDeviceName(channel.analog_device),state.device_state.name)
    if exchange:
      P = self.exchange(P)
    macros = { 'P':"{0}".format(P),
               'CR':'{0}'.format(card.link_node.crate.id),
               'CA':'{0}'.format(card.number),
               'CH':'{0}'.format(channel.number),
               'ID':'{0}'.format(channel.analog_device.id),
               'MASK':'{0}'.format(state.device_state.mask) }
    self.write_epics_db(path=path,filename='analog_devices.db', template_name="cn_analog_fault.template", macros=macros)    

  def __export_cn_device_input(self,channel,card):
    if card.link_node.get_cn1_prefix() == 'SIOC:SYS0:MP01':
      macros = self.get_cn_device_macros(channel,card,False)
      self.write_epics_db(path=self.cn0_path,filename='device_inputs.db',template_name="cn_device_input.template", macros=macros)
    elif card.link_node.get_cn1_prefix() == 'SIOC:SYS0:MP02':   
      macros = self.get_cn_device_macros(channel,card,False)
      self.write_epics_db(path=self.cn1_path,filename='device_inputs.db',template_name="cn_device_input.template", macros=macros)
    if card.link_node.get_cn2_prefix() == 'SIOC:SYS0:MP03':
      macros = self.get_cn_device_macros(channel,card,True)
      self.write_epics_db(path=self.cn2_path,filename='device_inputs.db',template_name="cn_device_input.template", macros=macros)

  def get_cn_device_macros(self,channel,card,exchange=False):
    name=self.mps_names.getInputPvFromChannel(channel)
    states = self.get_alarm_state(channel.alarm_state)
    if exchange:
      name = self.exchange(name)
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

  def __export_virtual(self,channel,card):
    n = channel.monitored_pvs
    if "WIGG" in n:
      ex = "_IN"
      if channel.number%2 !=0:
        ex="_OUT"
      n = "{0}{1}".format(channel.monitored_pvs[:-8], ex)
    states = self.get_alarm_state(channel.alarm_state)
    vmacros = {  "P":channel.monitored_pvs+'_THR',
                 "R":channel.name,
                 "N":n,
                 "INPV":channel.monitored_pvs,
                 "ALSTATE":str(channel.alarm_state),
                 "NALSTATE":str(to_bool(not channel.alarm_state)),
                 "ZSV":states[0],
                 "OSV":states[1],
                 "BIT":"{:02d}".format(channel.number-32).format,
                 "ZNAM":channel.z_name,
                 "ONAM":channel.o_name, 
                 "GID":"{0}".format(card.number),
                 "SCAN":".2 second"}
    if (channel.device_input.digital_device.device_type.name == 'WDOG'):
      self.__write_virtual_wdog_db(path=self.app_path, macros=vmacros)
      cha = '{0}_WDOG_RBV'.format(n)
    elif (channel.device_input.digital_device.device_type.name == 'EPICS'):
      self.__write_virtual_db(path=self.app_path, macros=vmacros)
      cha = '{0}_INPUT_RBV'.format(n)

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

  def __write_virtual_wdog_db(self, path, macros):
      """
      Write records for digital virtual watchdog inputs
      """
      self.write_epics_db(path=path,filename='mps.db', template_name="watchdog.template", macros=macros)

  def __write_virtual_db(self, path, macros):
      """
      Write records for digital virtual inputs
      """
      self.write_epics_db(path=path,filename='mps.db', template_name="virtual.template", macros=macros)

  def __write_mps_virt_db(self, path, macros):
      """
      Write the base mps records to the application EPICS database file.
      These records will be loaded once per each device.
      """
      self.write_epics_db(path=path,filename='mps.db', template_name="has_virtual.template", macros=macros)

  def __write_ana_config(self, path, macros):
      """
      Write the analog configuration section to the application configuration file.
      This configuration will be load by all applications.
      """
      self.write_fw_config(path=path, template_name="analog_settings.template", macros=macros)

  def __write_analog_db(self, path, macros):
      """
      Write the records for analog inputs to the application EPICS database file.

      These records will be loaded once per each device.
      """
      self.write_epics_db(path=path,filename='mps.db', template_name="ln_combined_lc1_analog.template", macros=macros)

  def __write_bsa_db(self, path, macros):
      """
      Write the base threshold record to the application EPICS database file.
      These records will be loaded once per each fault.
      """
      self.write_epics_db(path=path,filename='mps.db', template_name="bsa.template", macros=macros)
        
  def __write_lc1_dc_db(self, path, macros):
      """
      Write lcls1 kicker threshold records to the application EPICS database file.
      These records will be loaded once per each fault.
      """
      self.write_epics_db(path=path,filename='mps.db', template_name="lc1_bend.template", macros=macros)
  
  def __write_lc1_kick_db(self, path, macros):
      """
      Write lcls1 kicker threshold records to the application EPICS database file.
      These records will be loaded once per each fault.
      """
      self.write_epics_db(path=path,filename='mps.db', template_name="lc1_kick.template", macros=macros)

  def __write_thr_base_db(self, path, macros):
      """
      Write the base threshold record to the application EPICS database file.
      These records will be loaded once per each fault.
      """
      self.write_epics_db(path=path,filename='mps.db', template_name="thr_base.template", macros=macros)
    
  def __write_thr_db(self, path, macros):
      """
      Write the threshold records to the application EPICS database file.
      These records will be load once per each bit in each fault.
      """
      self.write_epics_db(path=path,filename='mps.db', template_name="thr.template", macros=macros)
