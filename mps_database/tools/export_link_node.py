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
import ipaddress

class ExportLinkNode(MpsReader):

  def __init__(self, db_file, template_path, dest_path,clean, verbose,session):
    MpsReader.__init__(self,db_file=db_file,dest_path=dest_path,template_path=template_path,clean=clean,verbose=verbose)
    self.verbose = verbose
    self.mps_names = MpsName(session)
    self.session = session

  def export_epics(self,ln):
    if self.verbose:
      print("  INFO: Working on LN {0}....".format(ln.lcls1_id))
    app_path = self.get_app_path(ln,ln.slot_number)
    salt = "0x3e"
    if ln.lcls1_id in [98, 202]:
      salt = "0"
    self.write_template(app_path,filename='config.yaml',template='salt.template',macros={"SLOTS":salt},type='link_node')
    prefix = ln.get_app_prefix()
    # Write generic PVs for what is installed where
    macros = {"P":prefix,
              "MPS_LINK_NODE_TYPE":'{0}'.format(self.link_node_type_to_number(ln.get_type())),
              "MPS_LINK_NODE_ID":'{0}'.format(ln.lcls1_id),
              "MPS_LINK_NODE_SIOC":'{0}'.format(ln.get_name()),
              "MPS_CRATE_LOCATION":'{0}'.format(ln.crate.location),
              "MPS_CPU_NAME":'{0}'.format(ln.cpu),
              "MPS_SHM_NAME":'{0}'.format(ln.get_shelf_manager()),
              "GROUP":'{0}'.format(ln.group),
              "IS_LN":'{0}'.format(1)}
    self.write_template(path=self.manager_path,filename='link_nodes.db',template="link_node_info.template", macros=macros,type='link_node')
    macros = {"P":prefix,
              "MPS_CONFIG_VERSION":self.config_version}
    self.write_template(path=app_path,filename='mps.db',template="config_version.template", macros=macros,type='link_node')
    self.__write_lc1_info_config(app_path,ln)
    #If no alalog cards in slot 2, write all channels are not available
    if ln.get_type() == 'Digital':
      self.write_template(app_path,filename='config.yaml',template='app_id.template',macros={"ID":"0"},type='link_node')
      for ch in range(0,6):
          macros = {"P":'{0}'.format(ln.get_app_prefix()),
                    "ATTR":"CH{0}".format(ch),
                    "CH":"{0}".format(ch)}
          self.write_template(app_path,filename='mps.env',template='waveform.template',macros=macros,type='link_node')
      for ch in range(0,4):
          macros = {"P":'{0}'.format(ln.get_app_prefix()),
                    "ATTR":"CH{0}".format(ch),
                    "CH":"{0}".format(ch)}
          self.write_template(app_path,filename='mps.env',template='gain.template',macros=macros,type='link_node')  
    slots = []
    for card in ln.cards:
      self.app_timeout_alarms(card)
      if card.slot_number not in slots:
        macros = {"P":card.get_pv_name(),
                  "SLOT":'{0}'.format(card.slot_number),
                  "SLOT_NAME":'{0}'.format(card.type.name),
                  "SLOT_SPARE":'{0}'.format(0),
                  "SLOT_PREFIX":card.get_pv_name(),
                  "SLOT_DESC":'{0}'.format(card.description)}
        self.write_template(path=self.manager_path,filename='link_nodes.db',template="link_node_slot_info.template", macros=macros,type='link_node')
        if len(card.analog_channels) > 0:
          for ch in card.analog_channels:
            self.write_ln_channel_info(ch,card)
        slots.append(card.slot_number)
    for slot in range(2,8):
      if slot not in slots:
        macros = {"P":"{0}:{1}".format(ln.get_pv_base(),slot),
                  "SLOT":'{0}'.format(slot),
                  "SLOT_NAME":'Spare',
                  "SLOT_SPARE":'{0}'.format(1),
                  "SLOT_PREFIX":'Spare',
                  "SLOT_DESC":'Spare'}
        self.write_template(path=self.manager_path,filename='link_nodes.db',template="link_node_slot_info.template", macros=macros,type='link_node')

  def export_cn_input_display(self,link_node,macros):
    input_display_filename = '{0}inputs/ln_{1}_inputs.json'.format(self.display_path,link_node.lcls1_id)
    self.write_json_file(input_display_filename,macros)

  def write_ln_channel_info(self,ch,card):
    macros = { "P": card.get_pv_name(),
               "CH":str(ch.number),
               "CH_NAME":ch.analog_device.description[:39],
               "CH_PVNAME":self.mps_names.getDeviceName(ch.analog_device)}
    self.write_template(path=self.manager_path,filename='link_nodes.db',template="channel_info.template", macros=macros,type='link_node')

  def app_timeout_alarms(self,card):
    cn = card.link_node.get_cn_prefix()
    macros = {'MPS_PREFIX':cn,
              'LN_GROUP':'{0}'.format(card.link_node.group),
              'ID':'{0}'.format(card.number)}
    file_path = '{0}timeout/group_{1}_{2}.alhConfig'.format(self.alarm_path,card.link_node.group,cn.split(':')[2].lower())
    self.write_alarm_file(path=file_path, template_name='mps_group.template', macros=macros)
      
  def __write_lc1_info_config(self,path,link_node):
      """
      Write the LCLS-I link node ID to the configuration file.
      """
      if link_node.lcls1_id == "0":
          ip_str = '0.0.168.192'.format(app["app_id"])
          print('ERROR: Found invalid link node ID (lcls1_id of 0)')
      else:
          ip_str = '{}.0.168.192'.format(link_node.lcls1_id)
      write = False
      ip_address = int(ipaddress.ip_address(ip_str))
      mask = 0
      remap_dig = link_node.get_digital_app_id()
      if remap_dig > 0:
        mask = 1
        write = True
     
      bpm_index = 0
      blm_index = 0
      remap_bpm = [0, 0, 0, 0, 0]
      remap_blm = [0, 0, 0, 0, 0]
      for card in link_node.cards:
        if card.slot_number == 2:
          write = True
        if card.type.name == 'BPM':
          if bpm_index < 5:
            remap_bpm[bpm_index] = card.number
            bpm_index +=1
          else:
            print(('ERROR: Cannot remap BPM app id {}, all remap slots are used already'.\
                    format(slot_info["app_id"])))
        elif card.type.name == "MPS Analog":
          if blm_index < 5:
            remap_blm[blm_index] = card.number
            mask |= 1 << (blm_index + 1 + 5) # Skip first bit and 5 BPM bits
            blm_index += 1
          else:
            print(('ERROR: Cannot remap BLM app id {}, all remap slots are used already'.\
                  format(slot_info["app_id"])))
      macros={"ID":'{0}'.format(link_node.lcls1_id),
                "IP_ADDR":str(ip_address),
                "REMAP_DIG":str(remap_dig),
                "REMAP_BPM1":str(remap_bpm[0]),
                "REMAP_BPM2":str(remap_bpm[1]),
                "REMAP_BPM3":str(remap_bpm[2]),
                "REMAP_BPM4":str(remap_bpm[3]),
                "REMAP_BPM5":str(remap_bpm[4]),
                "REMAP_BLM1":str(remap_blm[0]),
                "REMAP_BLM2":str(remap_blm[1]),
                "REMAP_BLM3":str(remap_blm[2]),
                "REMAP_BLM4":str(remap_blm[3]),
                "REMAP_BLM5":str(remap_blm[4]),
                "REMAP_MASK":str(mask),
                }
      if write:
          self.write_template(path=path,filename='config.yaml',template="lc1_info.template",macros=macros,type='link_node') 

  def writeCrateProfile(self,link_node,crate_profiles):
      rack = link_node.crate.location
      shm = link_node.get_shelf_manager()
      lc1_id = link_node.lcls1_id
      rows = []
      app = self.__find_slot2_digital(link_node)
      slot_type = 'N/A'
      slot_app_id = 'N/A'
      slot_description = "Not In MPS"
      if len(app.digital_channels) > 0:
        slot_type = app.type.name
        slot_app_id = app.number
        slot_description = app.description
      rows.append(['RTM',slot_app_id,slot_type,slot_description])
      slot_type = 'N/A'
      slot_app_id = 'N/A'
      slot_description = "Not In MPS"
      app = self.__find_slot2_analog(link_node)
      if app is not None:
        if len(app.digital_channels) > 0 or len(app.analog_channels) > 0:
          slot_type = app.type.name
          slot_app_id = app.number
          slot_description = app.description   
      rows.append(['2',slot_app_id,slot_type,slot_description])       
      for slot in range(3,8):
        slot_type = 'N/A'
        slot_app_id = 'N/A'
        slot_description = "Not In MPS"
        apps = [app for app in link_node.cards if app.slot_number == slot]   
        if len(apps) > 1:
          print("ERROR: Too many apps!")
          continue   
        if len(apps) == 1:
          if len(apps[0].digital_channels) > 0 or len(apps[0].analog_channels) > 0:
            slot_type = '{0}'.format(apps[0].type.name)
            slot_app_id = '{0}'.format(apps[0].number)
            slot_description = '{0}'.format(apps[0].description)
        slot_report = slot
        rows.append([slot_report,slot_app_id,slot_type,slot_description])
      crate_profiles.crateProfile(lc1_id,shm,rack,rows)

  def __find_slot2_digital(self,link_node):
    apps = [app for app in link_node.cards if app.slot_number == 1]
    for app in apps:
      if app.type.name == "MPS Digital":
        return app
    return None

  def __find_slot2_analog(self,link_node):
    apps = [app for app in link_node.cards if app.slot_number == 2]
    for app in apps:
      if app.type.name == "MPS Analog":
        return app
    return None

  def generate_crate_display(self,link_node):
    width = 347
    header_height = 30
    widget_height = 20
    height = header_height + widget_height * 8 + 5
    macros = {'HEADER_HEIGHT':'{0}'.format(int(header_height)),
              'WIDTH':'{0}'.format(int(width)),
              'HEIGHT':'{0}'.format(int(height)),
              'P':'{0}'.format(link_node.get_app_prefix())}
    filename = '{0}slots/LinkNode{1}_slot.ui'.format(self.display_path,link_node.lcls1_id)
    self.__write_crate_header(path=filename,macros=macros)
    x = 5
    app = self.__find_slot2_digital(link_node)
    y = header_height + widget_height
    if app is not None:
      self.__write_slot_into(2,link_node,app,x,y,filename,True)
    app = self.__find_slot2_analog(link_node)
    y = header_height + 2*widget_height
    if app is not None:
      self.__write_slot_into(2,link_node,app,x,y,filename)
    else:
      macros = {'SLOT':'2',
                'X':'{0}'.format(int(x)),
                'Y':'{0}'.format(int(y))}
      self.__write_empty_slot(path=filename,macros=macros)    
    for slot in range(3,8):
      y = header_height + slot * widget_height
      apps = [app for app in link_node.cards if app.slot_number == slot]   
      if len(apps) > 1:
        print("ERROR: Too many apps!")
        continue   
      if len(apps) < 1:
        macros = {'SLOT':'{0}'.format(int(slot)),
                  'X':'{0}'.format(int(x)),
                  'Y':'{0}'.format(int(y))}
        self.__write_empty_slot(path=filename,macros=macros)
      if len(apps) == 1:
        self.__write_slot_into(slot,link_node,apps[0],x,y,filename)
    self.__write_crate_footer(path=filename,macros=macros)

  def __write_crate_header(self, path,macros):
      self.write_ui_file(path=path, template_name="ln_crate_header.tmpl", macros=macros)

  def __write_crate_footer(self, path,macros):
      self.write_ui_file(path=path, template_name="ln_crate_footer.tmpl", macros=macros)

  def __write_crate_embed(self,path,macros):
      self.write_ui_file(path=path, template_name="ln_crate_embed.tmpl", macros=macros)

  def __write_empty_slot(self,path,macros):
      self.write_ui_file(path=path, template_name="ln_crate_empty.tmpl", macros=macros)

  def __write_slot_into(self,slot,link_node,app,x,y,filename,digital=False):
    fn = 'mps_ln_application.ui'
    slot_publish = slot
    postfix = 'APP_ID'
    inst = 1
    if inst == 2:
      inst = 1
    if digital:
      slot_publish = 'RTM'
      postfix = 'DIG_APPID_RBV'
      fn = 'mps_ln_digital.ui'
    type = 'MPS'
    if app.type.name == 'BPM':
      type = 'BPM'
    if app.type.name == 'BCM/BLEN':
      type = 'BCM/BLEN'  
    if app.type.name == 'MPS Analog':
      type = 'MPS_AI'
    if app.type.name == 'MPS Digital':
      type = 'MPS_DI'
    if app.type.name == 'LLRF':
      type = 'LLRF'
    if app.type.name == 'Wire Scanner':
      type = 'WIRE'
    macros = {'SLOT':'{0}'.format(slot_publish),
              'CRATE':link_node.location,
              'CN':link_node.get_cn_prefix(),
              'AID':'{0}'.format(app.number),
              'MPS_PREFIX':'{0}'.format(app.get_pv_name()),
              'TYPE':type,
              'DESC':'{0}'.format(app.description),
              'X':'{0}'.format(int(x)),
              'Y':'{0}'.format(int(y)),
              'POSTFIX':postfix,
              'FILENAME':fn,
              'LOCA':'{0}'.format(app.area),
              'IOC_UNIT':app.location,
              'INST':'{0}'.format(inst)}
    self.__write_crate_embed(path=filename,macros=macros)
