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

class ExportApplication(MpsReader):

  def __init__(self, db_file,template_path,dest_path,clean,verbose,session):
    MpsReader.__init__(self,db_file=db_file,dest_path=dest_path,template_path=template_path,clean=clean,verbose=verbose)
    self.verbose = verbose
    self.mps_names = MpsName(session)
    self.session = session

  def export_epics(self,app):
    if self.verbose:
      print("    INFO: Working on application {0}, slot {1}....".format(app.number,app.slot_number))
    app_path = self.get_app_path(app.link_node,app.slot_number)
    if app.slot_number != 2:
      macros = {"P":app.get_pv_name(),"THR_LOADED":"0"}
      self.write_template(app_path,filename='mps.db',template='app_db.template',macros=macros,type="link_node")
      macros = {"P":app.get_pv_name(),"VER":self.config_version,"LOC":app.link_node.crate.location,"SLOT":"{}".format(app.slot_number),"DATE":datetime.datetime.now().strftime('%Y.%m.%d-%H:%M:%S')}
      self.write_template(app_path,filename='mps.env',template='prefix_env.template',macros=macros,type='link_node')
      if app.slot_number == 1:
      #  self.write_iocinfo_env(app,app_path)
        self.write_mode_db(app,app_path)
    if app.type.name == 'MPS Digital':
      self.write_template(app_path,filename='config.yaml',template='dig_app_id.template',macros={"ID":str(app.number)},type='link_node')
    else:
      self.write_template(app_path,filename='config.yaml',template='app_id.template',macros={"ID":str(app.number)},type='link_node')
      self.write_template(app_path,filename='config.yaml',template='thresholds_off.template',macros={},type='link_node')
      if app.type.name == 'MPS Analog':
        if app.slot_number > 2:
          self.write_mode_db(app,app_path)
          macros = {"P":app.get_pv_name(),
                    "MPS_CONFIG_VERSION":self.config_version}
          self.write_template(path=app_path,filename='mps.db',template="config_version.template", macros=macros,type='link_node')
          macros = {'CPU':app.link_node.cpu,
                    'SHELF':app.link_node.get_shelf_manager(),
                    'SLOT':'{0}'.format(app.slot_number),
                    'FILE':'an{0}.out'.format(app.number)}
          tmpl = '{}scripts/program_fw.template'.format(self.template_path)
          fname = '{0}scripts/program_an_fw.sh'.format(self.dest_path)
          self.write_file_from_template(file=fname, template=tmpl, macros=macros)
        proc = 3
        if app.link_node.get_name() in ['sioc-bsyh-mp03','sioc-bsys-mp04']:
          proc = 0
        amc = 2 # B0 Only
        bays = 1
        tplt = 'analog_b0_only.template'
        if len(app.analog_channels) > 3:
          amc = 0 # Both
          bays = 2
          tplt = 'analog_both_bays.template'
        if len(app.analog_channels) == 0:
          amc = 3 # None
          bays = 0
          tplt = 'analog_no_bays.template'
          for ch in range(0,6):
            macros = {"P":'{0}'.format(app.get_pv_name(),ch),
                      "ATTR":"CH{0}".format(ch),
                      "CH":"{0}".format(ch)}
            self.write_template(app_path,filename='mps.env',template='waveform.template', macros=macros,type='link_node')
            if ch < 4:
              self.write_template(app_path,filename='mps.env',template='gain.template', macros=macros,type='link_node')
        self.write_template(app_path,filename='config.yaml',template='processing.template',macros={"PROC":str(proc)},type='link_node')
        self.write_template(app_path,filename='config.yaml',template='bays_present.template',macros={"DIS":"{0}".format(amc)},type='link_node')
        self.write_template(app_path,filename='mps.db',template=tplt,macros={'P':app.get_pv_name()},type='link_node')
        self.write_template(app_path,filename='mps.db',template='num_trig.template',macros={"P":app.get_pv_name(),"NUM":"{0}".format(bays)},type='link_node')

  def export_cn_app_id(self,card):
    mode = '1'
    if card.link_node.area in self.hard_areas:
      mode = 'MPS:UNDH:1:FACMODE CPP MSI'
    if card.link_node.area in self.soft_areas:
      mode = 'MPS:UNDS:1:FACMODE CPP MSI'
    if card.link_node.area in ['CLTS']:
      mode = '0'
    if len(card.digital_channels) == 0:
      if len(card.analog_channels) == 0:
        mode = '0'
    if card.type.name == 'Wire Scanner':
      mode = '0'
    macros = { 'APP_ID':'{0}'.format(card.number),
               'TYPE':'{0}'.format(card.name),
               'LOCA':'{0}'.format(card.link_node.crate.location),
               'SLOT':'{0}'.format(card.slot_number),
               'ID':'{0}'.format(card.id),
               'INPV':mode }
    self.write_template(self.get_cn_path(card.link_node),filename='apps.db',template='cn_app_timeout.template',macros=macros,type='central_node')

  def write_cn_status_macros(self,card,global_macros):
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
    global_macros.append(macros)

  def write_cn_status_macro_file(self,macros):
    filename = '{0}status/cn_status.json'.format(self.display_path)
    self.write_json_file(filename, macros)

  def write_mode_db(self,app,path):
    if app.slot_number < 3:
      ide = 'LN{0}'.format(app.link_node.lcls1_id)
    else:
      ide = 'AN{0}'.format(app.number)
    loca = '{0}-S{1}'.format(app.link_node.crate.location,app.slot_number)
    macros={"P":app.get_pv_name()}
    self.write_template(path,filename="mps.db",template="alarm_wdog.template",macros=macros,type='link_node')
    macros={"P":app.get_pv_name(),
            "ID":ide,
            "LOCA":loca}
    self.write_template(self.manager_path,filename="link_nodes.db",template="ln_id.template",macros=macros,type='link_node')

  def write_iocinfo_env(self,app,path):
    macros={"AREA":app.area,
            "LOCATION":app.location,
            "LOC_IDX":app.location.replace('MP', ''),
            "SLOT":'{0}'.format(app.slot_number)}
    self.write_template(path,filename='mps.env',template='ioc_info.template',macros=macros,type='link_node')

  def export_displays(self,app):
    if app.type.name == 'MPS Digital':
      return
    else:
      self.export_ln_analog(app)

  def export_ln_analog(self,app):
    app_macros = []
    for channel in app.analog_channels:
      dn = '{0}'.format(self.mps_names.getDeviceName(channel.analog_device))
      dt = dn
      vis = True
      file = 'mps_lblm_thresholds.ui'
      if channel.analog_device.device_type.name == 'WF':
        dn = '{0} Fast Waveform'.format(self.mps_names.getDeviceName(channel.analog_device))
        vis = False
      if channel.analog_device.name.split(':')[1] in ['LBLM','PBLM']:
        dt = '{0}:I0_LOSS'.format(dt)
        file = 'mps_lblm_thresholds.ui'
      if channel.analog_device.name.split(':')[1] in ['BPMS']:
        file = 'mps_bpm_thresholds.ui'
      if channel.analog_device.device_type.name in ['BACT']:
        file = 'mps_magnet_thresholds.ui'
      if channel.analog_device.name.split(':')[1] in ['CBLM']:
        file = 'mps_cblm_thresholds.ui'
      macros = {}
      macros['P'] = '{0}'.format(app.get_pv_name())
      macros['CH'] = '{0}'.format(channel.number)
      macros['DEVICE_NAME'] = dn
      macros['PV_PREFIX'] = '{0}'.format(self.mps_names.getDeviceName(channel.analog_device))
      macros['VIS'] = '{0}'.format(vis)
      macros['DEVICE_THR'] = dt
      macros['FILE'] = file
      app_macros.append(macros)
    filename = '{0}thresholds/app{1}_chan.json'.format(self.display_path,app.number)
    self.write_json_file(filename, app_macros)
      
