#!/usr/bin/env python
from mps_database.mps_config import MPSConfig, models, runtime
from sqlalchemy import MetaData
from mps_database.tools.mps_names import MpsName
from mps_database.tools.mps_reader import MpsReader, MpsDbReader
from mps_database.tools.export_apps import ExportApplication
from mps_database.tools.input_display import InputDisplay
import argparse
import time
import yaml
import os
import sys
import datetime
import ipaddress

class ExportLinkNode(MpsReader):

  def __init__(self, db_file, template_path, dest_path,clean, verbose):
    MpsReader.__init__(self,db_file=db_file,dest_path=dest_path,template_path=template_path,clean=clean,verbose=verbose)
    self.export_app = ExportApplication(db_file,template_path,dest_path,False,verbose)
    self.verbose = verbose

  def export(self,mps_db_session,link_nodes=None,crate_profiles=None,input_report=None,cn_disp=None,appendixA=None):
      # Extract the application information
      if link_nodes is None:
        link_nodes = mps_db_session.query(models.LinkNode).filter(models.LinkNode.slot_number == 2).all()
      for link_node in link_nodes:
        app_path = self.get_app_path(link_node,link_node.slot_number)
        # only do this stuff for "link nodes" in slot 2
        macros = {'CPU':link_node.cpu,
                  'SHELF':link_node.get_shelf_manager(),
                  'SLOT':'2'}
        filen = '{0}scripts/program_ln_fw_group{1}.sh'.format(self.dest_path,link_node.group)
        tmpl = '{}scripts/program_fw.template'.format(self.template_path)
        self.write_file_from_template(file=filen, template=tmpl, macros=macros)
        filen = '{0}scripts/reboot_nodes.sh'.format(self.dest_path)
        tmpl = '{}scripts/reboot_nodes.template'.format(self.template_path)
        self.write_file_from_template(file=filen, template=tmpl, macros={'LN':link_node.get_name()})
        self.__write_salt_fw(path=app_path,macros={"SLOTS":"0x3e"})
        self.__write_header_env(path=app_path, macros={"MPS_LINK_NODE":link_node.get_name()})
        idx = link_node.slot_number
        self.__write_iocinfo_env(path=app_path, macros={"AREA":link_node.area,
                                                        "LOCATION":link_node.location,
                                                        "LOC_IDX":link_node.location.replace('MP', ''),
                                                        "C_IDX":"{0}".format(link_node.get_app_number())})
        macros = {"P":link_node.get_app_prefix(),
                  "MPS_CONFIG_VERSION":self.config_version,
                  "MPS_LINK_NODE_TYPE":'{0}'.format(self.link_node_type_to_number(link_node.get_type())),
                  "MPS_LINK_NODE_ID":'{0}'.format(link_node.lcls1_id),
                  "MPS_LINK_NODE_SIOC":'{0}'.format(link_node.get_name()),
                  "MPS_CRATE_LOCATION":'{0}'.format(link_node.crate.location),
                  "MPS_CPU_NAME":'{0}'.format(link_node.cpu),
                  "MPS_SHM_NAME":'{0}'.format(link_node.get_shelf_manager()),
                  "GROUP":'{0}'.format(link_node.group),
                  "IS_LN":'{0}'.format(1)}
        self.write_epics_db(path=app_path,filename='mps.db', template_name="link_node_info.template", macros=macros)
        #If no alalog cards in slot 2, write all channels are not available
        if link_node.get_type() == 'Digital':
          self.__write_app_id_config(path=app_path, macros={"ID":"0","PROC":"3"}) # If there are no analog cards, set ID to invalid
          for ch in range(0,6):
            macros = { "P": link_node.get_app_prefix(),
                       "CH":str(ch),
                       "CH_NAME":"Not Available",
                       "CH_PVNAME":"None",
                       "CH_SPARE":"1",
                       "TYPE":"None"
                     }
            self.write_link_node_channel_info_db(path=app_path, macros=macros)
            macros = {"P":'{0}:CH{1}_WF'.format(link_node.get_app_prefix(),ch),
                      "CH":"{0}".format(ch)}
            self.write_epics_env(path=app_path, template_name='waveform.template', macros=macros)
            macros = {"P":'{0}'.format(link_node.get_app_prefix()),
                      "CH":"{0}".format(ch),
                      "ATTR0":"I0_CH{0}".format(ch),
                      "ATTR1":"I1_CH{0}".format(ch)}
            self.write_epics_env(path=app_path, template_name='bsa.template', macros=macros)
        slots = []
        cards = link_node.cards
        if link_node.slot_number == 2:
          self.inputDisplay = InputDisplay(link_node.lcls1_id)
          if crate_profiles is not None:
            crate_profiles.startLinkNode(link_node.lcls1_id,link_node.crate.location)
            self.writeCrateProfile(link_node,crate_profiles)
          if appendixA is not None:
            self.writeAppendixA(link_node,appendixA)
          self.__write_lc1_info_config(app_path,link_node)
          self.__generate_crate_display(link_node)
          for card in cards:
            self.app_timeout_alarms(card)
            if cn_disp is not None:
              self.write_cn_status_macros(cn_disp,card)
            self.export_app.export(mps_db_session,card,self.inputDisplay)
            if card.slot_number not in slots:
              macros = {"P":link_node.get_app_prefix(),
                        "SLOT":'{0}'.format(card.slot_number),
                        "SLOT_NAME":'{0}'.format(card.type.name),
                        "SLOT_SPARE":'{0}'.format(0),
                        "SLOT_PREFIX":card.get_pv_name(),
                        "SLOT_DESC":'{0}'.format(card.description)}
              self.__write_link_node_slot_info_db(path=app_path, macros=macros)
            slots.append(card.slot_number)
          input_display_filename = '{0}inputs/ln_{1}_inputs.json'.format(self.display_path,link_node.lcls1_id)
          self.write_json_file(input_display_filename,self.inputDisplay.get_macros()) 
          if input_report is not None:
            rows = self.inputDisplay.get_input_report_rows()
            if len(rows) > 0:
              input_report.startLinkNode(link_node.lcls1_id,link_node.crate.location)
              input_report.writeAppInputs(rows)
          for slot in range(2,8):
            if slot not in slots:
              macros = {"P":link_node.get_app_prefix(),
                        "SLOT":'{0}'.format(slot),
                        "SLOT_NAME":'Spare',
                        "SLOT_SPARE":'{0}'.format(1),
                        "SLOT_PREFIX":'Spare',
                        "SLOT_DESC":'Spare'}
              self.__write_link_node_slot_info_db(path=app_path, macros=macros)

  def app_timeout_alarms(self,card):
    cn = card.link_node.get_cn_prefix()
    macros = {'MPS_PREFIX':cn,
              'LN_GROUP':'{0}'.format(card.link_node.group),
              'ID':'{0}'.format(card.number)}
    file_path = '{0}timeout/group_{1}_{2}.alhConfig'.format(self.alarm_path,card.link_node.group,cn.split(':')[2].lower())
    self.write_alarm_file(path=file_path, template_name='mps_group.template', macros=macros)
    

  def write_cn_status_macros(self,cn_disp,card):
    macros = {}
    macros['GROUP'] = card.link_node.group
    macros['LN'] = card.link_node.lcls1_id
    if card.slot_number > 1:
      macros['SLOT'] = '{0}'.format(card.slot_number)
    else:
      macros['SLOT'] = 'RTM'
    macros['APP'] = card.number
    macros['P'] = card.get_pv_name()
    macros['CRATE'] = card.link_node.crate.location
    macros['CN'] = card.link_node.get_cn_prefix()
    cn_disp.add_macros(macros)

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
          self.write_fw_config(path=path, template_name="lc1_info.template", macros=macros) 

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

  def writeAppendixA(self,link_node,appendixA):
      shouldWrite = False
      rack = link_node.crate.location
      shm = link_node.get_shelf_manager()
      lc1_id = link_node.lcls1_id
      rows = []
      app = self.__find_slot2_digital(link_node)
      if len(app.digital_channels) > 0:
        shouldWrite = True
        slot_app_id = app.number
        slot_prefix = app.get_pv_name()
        rows.append(['RTM',slot_app_id,slot_prefix])
      app = self.__find_slot2_analog(link_node)
      if app is not None:
        if len(app.digital_channels) > 0 or len(app.analog_channels) > 0:
          shouldWrite = True
          slot_app_id = app.number
          slot_prefix = app.get_pv_name()
          rows.append(['2',slot_app_id,slot_prefix])       
      for slot in range(3,8):
        apps = [app for app in link_node.cards if app.slot_number == slot]   
        if len(apps) > 1:
          print("ERROR: Too many apps!")
          continue   
        if len(apps) == 1:
          if len(apps[0].digital_channels) > 0 or len(apps[0].analog_channels) > 0:
            shouldWrite = True
            slot_app_id = '{0}'.format(apps[0].number)
            slot_prefix = apps[0].get_pv_name()
            slot_report = slot
            rows.append([slot_report,slot_app_id,slot_prefix])
      if shouldWrite:
        appendixA.startLinkNode(link_node.lcls1_id,link_node.crate.location)
        appendixA.appendixA(lc1_id,shm,rack,rows)

  def __generate_crate_display(self,link_node):
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

  def __write_slot_into(self,slot,link_node,app,x,y,filename,digital=False):
    fn = 'mps_ln_application.ui'
    slot_publish = slot
    postfix = 'APP_ID'
    inst = slot
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
              'LOCA':'{0}'.format(link_node.area),
              'IOC_UNIT':'{0}'.format(app.location),
              'INST':'{0}'.format(inst)}
    self.__write_crate_embed(path=filename,macros=macros)

  def __write_header_env(self, path, macros):
      """
      Write the header for the MPS file containing environmental variables.
      This environmental variable will be loaded by all applications.
      """
      self.write_epics_env(path=path, template_name="header.template", macros=macros)   

  def __write_iocinfo_env(self, path, macros):
      """
      Write the LN IOC related environmental variable file.

      This environmental variable will be loaded by all link nodes.
      """
      self.write_epics_env(path=path, template_name="ioc_info.template", macros=macros)

  def __write_salt_fw(self,path,macros):
      self.write_fw_config(path=path, template_name="salt.template", macros=macros)

  def __write_link_node_slot_info_db(self, path, macros):
      self.write_epics_db(path=path,filename='mps.db', template_name="link_node_slot_info.template", macros=macros)

  def __write_app_id_config(self, path, macros):
      """
      Write the appID configuration section to the application configuration file.
      This configuration will be load by all applications.
      """
      self.write_fw_config(path=path, template_name="app_id.template", macros=macros)

  def __write_crate_header(self, path,macros):
      self.write_ui_file(path=path, template_name="ln_crate_header.tmpl", macros=macros)

  def __write_crate_footer(self, path,macros):
      self.write_ui_file(path=path, template_name="ln_crate_footer.tmpl", macros=macros)

  def __write_crate_embed(self,path,macros):
      self.write_ui_file(path=path, template_name="ln_crate_embed.tmpl", macros=macros)

  def __write_empty_slot(self,path,macros):
      self.write_ui_file(path=path, template_name="ln_crate_empty.tmpl", macros=macros)

