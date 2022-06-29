#!/usr/bin/env python
from mps_database.mps_config import MPSConfig, models, runtime
from sqlalchemy import MetaData, Column
from mps_database.tools.mps_names import MpsName
from mps_database.tools.mps_reader import MpsReader, MpsDbReader
import math
import argparse
import time
import yaml
import os
import sys

class ExportCnExtras(MpsReader):

  def __init__(self, db_file, template_path, dest_path,clean, verbose):
    MpsReader.__init__(self,db_file=db_file,dest_path=dest_path,template_path=template_path,clean=clean,verbose=verbose)
    self.verbose = verbose
    self.bc_names = []
    self.bc_sevr = []

  def export_conditions(self,mps_db_session):
    if self.verbose:
      print('INFO: Begin Export Conditions')
    macros = {'VERSION':'{0}'.format(self.config_version)}
    self.write_epics_db(path=self.cn1_path,filename='conditions.db',template_name="cn_config_version.template", macros=macros)
    self.write_epics_db(path=self.cn2_path,filename='conditions.db',template_name="cn_config_version.template", macros=macros)
    self.write_epics_db(path=self.cn3_path,filename='conditions.db',template_name="cn_config_version.template", macros=macros)
    conditions = mps_db_session.query(models.Condition).all()
    for cond in conditions:
      condition_input = mps_db_session.query(models.ConditionInput).filter(models.ConditionInput.condition_id == cond.id).one()
      flt = condition_input.fault_state.fault
      fault_input = mps_db_session.query(models.FaultInput).filter(models.FaultInput.fault_id == flt.id).one()
      device = mps_db_session.query(models.Device).filter(models.Device.id == fault_input.device_id).one()
      macros = { 'NAME':'{0}'.format(cond.name.upper().replace(' ','_')),
                 'DESC':'{0}'.format(cond.description), 
                 'ID':'{0}'.format(cond.id) }
      if device.card.link_node.get_cn_prefix() == 'SIOC:SYS0:MP01':
        self.write_epics_db(path=self.cn1_path,filename='conditions.db',template_name="cn_condition.template", macros=macros)
      elif device.card.link_node.get_cn_prefix() == 'SIOC:SYS0:MP02':
        self.write_epics_db(path=self.cn2_path,filename='conditions.db',template_name="cn_condition.template", macros=macros)
      if device.card.link_node.get_cn_prefix() == 'SIOC:SYS0:MP03':
        self.write_epics_db(path=self.cn3_path,filename='conditions.db',template_name="cn_condition.template", macros=macros)
    if self.verbose:
      print('........Done Export Conditions')

  def export_destinations(self,mps_db_session):
    if self.verbose:
      print('INFO: Begin Export Destinations')
    destinations = mps_db_session.query(models.BeamDestination).all()
    beamClasses = mps_db_session.query(models.BeamClass).all()
    macros = { 'NUM':'{0}'.format(len(beamClasses))}
    self.write_epics_db(path=self.cn1_path,filename='destinations.db',template_name="cn_num_beam_classes.template", macros=macros)
    self.write_epics_db(path=self.cn2_path,filename='destinations.db',template_name="cn_num_beam_classes.template", macros=macros)
    self.write_epics_db(path=self.cn3_path,filename='destinations.db',template_name="cn_num_beam_classes.template", macros=macros)
    self.bc_names.append('Full')
    self.bc_sevr.append('NO_ALARM')
    for bc in beamClasses:
      self.bc_names.append(bc.name)
      if bc.number < 2:
        self.bc_sevr.append("MAJOR")
      elif bc.number in [2,3,5]:
        self.bc_sevr.append("MINOR")
      else:
        self.bc_sevr.append("NO_ALARM")
      macros = { 'NUM':'{0}'.format(bc.number),
                 'NAME':'{0}'.format(bc.name),
                 'DESC':'{0}'.format(bc.description),
                 'CHRG':'{0}'.format(bc.total_charge),
                 'SPACE':'{0}'.format(bc.min_period),
                 'TIME':'{0}'.format(bc.integration_window) }
      self.write_epics_db(path=self.cn1_path,filename='destinations.db',template_name="cn_beam_class_definition.template", macros=macros)
      self.write_epics_db(path=self.cn2_path,filename='destinations.db',template_name="cn_beam_class_definition.template", macros=macros)
      self.write_epics_db(path=self.cn3_path,filename='destinations.db',template_name="cn_beam_class_definition.template", macros=macros)
    for dest in destinations:
      macros = { 'DEST':'{0}'.format(dest.name.upper()),
                 'ID':'{0}'.format(dest.id),
                 'SHIFT':'{0}'.format(dest.id-1),
                 'SHIFT1':'{0}'.format(16+dest.id-1) }
      self.write_epics_db(path=self.cn1_path,filename='destinations.db',template_name="cn_beam_class_destination_header.template", macros=macros)
      self.write_epics_db(path=self.cn2_path,filename='destinations.db',template_name="cn_beam_class_destination_header.template", macros=macros)
      self.write_epics_db(path=self.cn3_path,filename='destinations.db',template_name="cn_beam_class_destination_header.template", macros=macros)
      for i in range(0,len(self.bc_names)):
        macros = {"STRING":self.mbbi_strings[i],
                  "VAL":self.mbbi_vals[i],
                  "BC_NAME":self.bc_names[i],
                  "BC_VAL":"{0}".format(i)}
        self.write_epics_db(path=self.cn1_path,filename='destinations.db',template_name="cn_destination_bc_entry.template", macros=macros)
        self.write_epics_db(path=self.cn2_path,filename='destinations.db',template_name="cn_destination_bc_entry.template", macros=macros)
        self.write_epics_db(path=self.cn3_path,filename='destinations.db',template_name="cn_destination_bc_entry.template", macros=macros)
      macros = { 'DEST':'{0}'.format(dest.name.upper()),
                 'ID':'{0}'.format(dest.id) }
      self.write_epics_db(path=self.cn1_path,filename='destinations.db',template_name="cn_destination_force_bc.template", macros=macros)
      self.write_epics_db(path=self.cn2_path,filename='destinations.db',template_name="cn_destination_force_bc.template", macros=macros)
      self.write_epics_db(path=self.cn3_path,filename='destinations.db',template_name="cn_destination_force_bc.template", macros=macros)
      macros = { 'DEST':'{0}'.format(dest.name.upper())}
      self.write_epics_db(path=self.cn1_path,filename='destinations.db',template_name="cn_bc_header.template", macros=macros)
      self.write_epics_db(path=self.cn2_path,filename='destinations.db',template_name="cn_bc_header.template", macros=macros)
      self.write_epics_db(path=self.cn3_path,filename='destinations.db',template_name="cn_bc_header.template", macros=macros)
      for i in range(1,len(self.bc_names)):
        macros = {"STRING":self.mbbi_strings[i-1],
                  "VAL":self.mbbi_vals[i-1],
                  "BC_NAME":self.bc_names[i],
                  "BC_VAL":"{0}".format(i-1),
                  "SEVR":self.mbbi_sevr[i-1],
                  "BC_SEVR":self.bc_sevr[i]}
        self.write_epics_db(path=self.cn1_path,filename='destinations.db',template_name="cn_bc_entry.template", macros=macros)
        self.write_epics_db(path=self.cn2_path,filename='destinations.db',template_name="cn_bc_entry.template", macros=macros)
        self.write_epics_db(path=self.cn3_path,filename='destinations.db',template_name="cn_bc_entry.template", macros=macros)
      self.write_epics_db(path=self.cn1_path,filename='destinations.db',template_name="cn_mbbi_finish.template", macros={})
      self.write_epics_db(path=self.cn2_path,filename='destinations.db',template_name="cn_mbbi_finish.template", macros={})
      self.write_epics_db(path=self.cn3_path,filename='destinations.db',template_name="cn_mbbi_finish.template", macros={})
    if self.verbose:
      print('........Done Export Destinations')

  def generate_area_displays(self,mps_db_session):
    self.initialize_mps_names(mps_db_session)
    self.mps_db_session = mps_db_session
    if self.verbose:
      print("INFO: Generating area displays")
    areas = ['GUNB','L3B','DOG','LTUH','LTUS','UNDH','UNDS','DMPH','DMPS','FEEH','FEES','SPS','SPH']
    for area in areas:
      areas = []
      areas.append(area)
      link_nodes = mps_db_session.query(models.LinkNode).filter(models.LinkNode.area == area).filter(models.LinkNode.slot_number == 2).order_by(models.LinkNode.lcls1_id).all()
      self.generate_area_display(area,link_nodes)
      self.generate_ln_alarms(area,link_nodes)
      self.generate_analog_display(area,areas)
    #now do special case areas
    #L0B includes L0B and COL0
    link_nodes = mps_db_session.query(models.LinkNode).filter(models.LinkNode.area.in_(['L0B','COL0','HTR'])).filter(models.LinkNode.slot_number == 2).order_by(models.LinkNode.lcls1_id).all()
    self.generate_area_display('L0B',link_nodes)
    self.generate_ln_alarms('L0B',link_nodes)
    self.generate_analog_display('L0B',['L0B','COL0','HTR'])
    #L1B includes L1B and BC1B
    link_nodes = mps_db_session.query(models.LinkNode).filter(models.LinkNode.area.in_(['L1B','BC1B'])).filter(models.LinkNode.slot_number == 2).order_by(models.LinkNode.lcls1_id).all()
    self.generate_area_display('L1B',link_nodes)
    self.generate_ln_alarms('L1B',link_nodes)
    self.generate_analog_display('L1B',['L1B','BC1B'])
    #L2B includes L2B and BC2B
    link_nodes = mps_db_session.query(models.LinkNode).filter(models.LinkNode.area.in_(['L2B','BC2B'])).filter(models.LinkNode.slot_number == 2).order_by(models.LinkNode.lcls1_id).all()
    self.generate_area_display('L2B',link_nodes)
    self.generate_ln_alarms('L2B',link_nodes)
    self.generate_analog_display('L2B',['L2B','BC2B'])
    #all BPNs
    areas = ['BPN13','BPN14','BPN15','BPN16','BPN17','BPN18','BPN19','BPN20','BPN21','BPN22','BPN23','BPN24','BPN25','BPN26','BPN27','BPN28']
    link_nodes = mps_db_session.query(models.LinkNode).filter(models.LinkNode.area.in_(areas)).filter(models.LinkNode.slot_number == 2).order_by(models.LinkNode.lcls1_id).all()
    self.generate_area_display('BYP',link_nodes)
    self.generate_ln_alarms('BYP',link_nodes)
    self.generate_analog_display('BYP',areas)
    #BSYsc
    link_nodes = mps_db_session.query(models.LinkNode).filter(models.LinkNode.area.in_(['BSYH','BSYS'])).filter(models.LinkNode.slot_number == 2).order_by(models.LinkNode.lcls1_id).all()
    self.generate_area_display('BSYsc',link_nodes)
    self.generate_ln_alarms('BSYsc',link_nodes)
    self.generate_analog_display('BSYsc',['BSYH','BSYS'])
    #BSYcu
    link_nodes = mps_db_session.query(models.LinkNode).filter(models.LinkNode.area.in_(['BSYH','BSYS','CLTS'])).filter(models.LinkNode.slot_number == 2).order_by(models.LinkNode.lcls1_id).all()
    self.generate_area_display('BSYcu',link_nodes)
    self.generate_ln_alarms('BSYcu',link_nodes)
    self.generate_analog_display('BSYcu',['BSYH','BSYS','CLTS'])
    #SPD
    link_nodes = mps_db_session.query(models.LinkNode).filter(models.LinkNode.area.in_(['SPD','SLTD'])).filter(models.LinkNode.slot_number == 2).order_by(models.LinkNode.lcls1_id).all()
    self.generate_area_display('SPD',link_nodes)
    self.generate_ln_alarms('SPD',link_nodes)
    self.generate_analog_display('SPD',['SPD','SLTD'])
    #finish up by generating display for MPS global which has all link nodes.  It is a json file with macros
    link_nodes = mps_db_session.query(models.LinkNode).filter(models.LinkNode.slot_number == 2).order_by(models.LinkNode.lcls1_id).all()
    ln_macros = []
    for ln in link_nodes:
      macros = {}
      macros['ID'] = ln.lcls1_id
      macros['P'] = "{0}".format(ln.get_app_prefix())
      macros['SLOT_FILE'] = 'LinkNode{0}_slot.ui'.format(ln.lcls1_id)
      macros['LN'] = ln.lcls1_id
      macros['LOCA'] = ln.area
      macros['IOC_UNIT'] = ln.location
      macros['INST'] = ln.get_app_number()
      ln_macros.append(macros)
    filename = '{0}mps_global_ln.json'.format(self.display_path)
    self.write_json_file(filename, ln_macros)

    if self.verbose:
      print("........Done Generating area displays")

  def generate_analog_display(self,area,areas):
    blm_dt = self.mps_db_session.query(models.DeviceType).filter(models.DeviceType.name == 'BLM').all()
    bpm_dt = self.mps_db_session.query(models.DeviceType).filter(models.DeviceType.name == 'BPMS').all()
    bcm_dt = self.mps_db_session.query(models.DeviceType).filter(models.DeviceType.name == 'TORO').all()
    blen_dt = self.mps_db_session.query(models.DeviceType).filter(models.DeviceType.name == 'BLEN').all()
    farc_dt = self.mps_db_session.query(models.DeviceType).filter(models.DeviceType.name == 'FARC').all()
    if len(blm_dt) > 0:
      blms = self.mps_db_session.query(models.AnalogDevice).filter(models.AnalogDevice.device_type == blm_dt[0]).filter(models.AnalogDevice.area.in_(areas)).order_by(models.AnalogDevice.z_location)
      self.generate_analog_display_single(blms,area,'BLM')
    if len(bpm_dt) > 0:
      bpms = self.mps_db_session.query(models.AnalogDevice).filter(models.AnalogDevice.device_type == bpm_dt[0]).filter(models.AnalogDevice.area.in_(areas)).order_by(models.AnalogDevice.z_location)
      self.generate_analog_display_single(bpms,area,'BPM')
    if len(bpm_dt) > 0:
      bcms = self.mps_db_session.query(models.AnalogDevice).filter(models.AnalogDevice.device_type == bcm_dt[0]).filter(models.AnalogDevice.area.in_(areas)).order_by(models.AnalogDevice.z_location)
      self.generate_analog_display_single(bcms,area,'BCM')
    if len(blen_dt) > 0:
      bcms = self.mps_db_session.query(models.AnalogDevice).filter(models.AnalogDevice.device_type == blen_dt[0]).filter(models.AnalogDevice.area.in_(areas)).order_by(models.AnalogDevice.z_location)
      self.generate_analog_display_single(bcms,area,'BCM')
    if len(farc_dt) > 0:
      bcms = self.mps_db_session.query(models.AnalogDevice).filter(models.AnalogDevice.device_type == farc_dt[0]).filter(models.AnalogDevice.area.in_(areas)).order_by(models.AnalogDevice.z_location)
      self.generate_analog_display_single(bcms,area,'BCM')


  def generate_analog_display_single(self,devices,area,type):
      macros = []
      for device in devices:
        if self.mps_names.getBlmType(device) in ['CBLM','WF']:
          wf = 'FAST'
        else:
          wf = 'MPS'
        fast = False
        if self.mps_names.getBlmType(device) in ['LBLM']:
          fast = True
        show_wf = False
        if type == 'BLM':
          show_wf = True
        faults = self.get_faults(device)
        for fault in faults:
          specific_macros = {}
          specific_macros['PV_PREFIX'] = self.mps_names.getDeviceName(device)
          specific_macros['THR'] = fault.name
          specific_macros['WF'] = wf
          specific_macros['HAS_FAST'] = fast
          specific_macros['SHOW_WF'] = show_wf
          macros.append(specific_macros)
      filename = '{0}/thresholds/{1}_{2}_thr.json'.format(self.display_path,area.upper(),type.upper())
      self.write_json_file(filename, macros)


  def generate_area_display(self,area,link_nodes):
      header_height = 30
      height = int(header_height + (len(link_nodes)*35))
      edl_height = int(header_height + (len(link_nodes)*30)+30)
      macros = { 'HEIGHT':'{0}'.format(int(height))}
      filename = '{0}areas/mps_{1}_link_nodes.ui'.format(self.display_path,area.lower())
      self.__write_area_header(path=filename,macros=macros)
      macros = { 'HEIGHT':'{0}'.format(int(edl_height))}
      filename_edl = '{0}edl/mps_{1}_link_nodes.edl'.format(self.display_path,area.lower())
      self.__write_area_edl_header(path=filename_edl,macros=macros)
      y = header_height
      edl_y = header_height+5
      groups = []
      for ln in link_nodes:
        macros = {"Y":"{0}".format(int(y)),
                  "PREFIX":"{0}".format(ln.get_app_prefix()),
                  "LN_ID":"{0}".format(ln.lcls1_id),
                  'SLOT_FILE':'LinkNode{0}_slot.ui'.format(ln.lcls1_id),
                  'LOCA':'{0}'.format(ln.area),
                  'IOC_UNIT':'{0}'.format(ln.location),
                  'INST':'{0}'.format(ln.get_app_number())}
        self.__write_area_embed(path=filename, macros=macros)
        macros = {"Y":"{0}".format(int(edl_y)),
                  "PREFIX":"{0}".format(ln.get_app_prefix()),
                  "LN_ID":"{0}".format(ln.lcls1_id),
                  'SLOT_FILE':'LinkNode{0}_slot.ui'.format(ln.lcls1_id),
                  'LOCA':'{0}'.format(ln.area),
                  'IOC_UNIT':'{0}'.format(ln.location),
                  'INST':'{0}'.format(ln.get_app_number())}
        self.__write_area_edl_embed(path=filename_edl, macros=macros)
        if ln.group not in groups:
          groups.append(ln.group)
        y += 35
        edl_y += 30
      edl_x = 14
      for group in groups:
        macros = {"GROUP":"{0}".format(group),
                  "X":"{0}".format(int(edl_x)),
                  "Y":"{0}".format(int(edl_y))}
        self.__write_area_edl_group(path=filename_edl,macros=macros)
        edl_x += 110
      self.__write_area_footer(path=filename,macros={"P":"P"})
      ln_macros = []
      for ln in link_nodes:
        macros = {}
        macros['LN'] = ln.lcls1_id
        ln_macros.append(macros)
      filename = '{0}areas/{1}_inputs_global.json'.format(self.display_path,area.lower())
      self.write_json_file(filename, ln_macros)

  def generate_ln_alarms(self,area,link_nodes):
      include_path = '{0}mpln_{1}_include.txt'.format(self.alarm_path,area)
      for ln in link_nodes:
        macros = {'PREFIX':ln.get_app_prefix(),
                  'LNID':'{0}'.format(ln.lcls1_id),
                  'IOC':ln.get_sioc_pv_base()}
        filename = 'mpln_{0}_{1}.alhConfig'.format(ln.area.lower(),ln.location.lower())
        path = '{0}areas/{1}'.format(self.alarm_path,filename)
        self.write_alarm_file(path=path, template_name='link_node_alarm.template', macros=macros)
        include_macros = {'AREA':area,
                          'FILENAME':filename}
        self.write_alarm_file(path=include_path, template_name='mps_include.template', macros=include_macros)

  def __write_area_header(self, path,macros):
      self.write_ui_file(path=path, template_name="ln_area_header.tmpl", macros=macros)

  def __write_area_footer(self, path,macros):
      self.write_ui_file(path=path, template_name="ln_area_footer.tmpl", macros=macros)

  def __write_area_embed(self,path,macros):
      self.write_ui_file(path=path, template_name="ln_area_embed.tmpl", macros=macros)

  def __write_area_edl_header(self, path,macros):
      self.write_ui_file(path=path, template_name="link_node_area_edl_header.tmpl", macros=macros)

  def __write_area_edl_group(self,path,macros):
      self.write_ui_file(path=path, template_name="link_node_group_button_edl.tmpl", macros=macros)

  def __write_area_edl_embed(self,path,macros):
      self.write_ui_file(path=path, template_name="link_node_area_edl_embed.tmpl", macros=macros)

      


