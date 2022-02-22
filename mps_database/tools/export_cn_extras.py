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

  def export_conditions(self,mps_db_session):
    if self.verbose:
      print('INFO: Begin Export Conditions')
    macros = {'VERSION':'{0}'.format(self.config_version)}
    self.write_epics_db(path=self.cn0_path,filename='conditions.db',template_name="cn_config_version.template", macros=macros)
    self.write_epics_db(path=self.cn1_path,filename='conditions.db',template_name="cn_config_version.template", macros=macros)
    self.write_epics_db(path=self.cn2_path,filename='conditions.db',template_name="cn_config_version.template", macros=macros)
    conditions = mps_db_session.query(models.Condition).all()
    for cond in conditions:
      condition_input = mps_db_session.query(models.ConditionInput).filter(models.ConditionInput.condition_id == cond.id).one()
      flt = condition_input.fault_state.fault
      fault_input = mps_db_session.query(models.FaultInput).filter(models.FaultInput.fault_id == flt.id).one()
      device = mps_db_session.query(models.Device).filter(models.Device.id == fault_input.device_id).one()
      macros = { 'NAME':'{0}'.format(cond.name.upper().replace(' ','_')),
                 'DESC':'{0}'.format(cond.description), 
                 'ID':'{0}'.format(cond.id) }
      if device.card.link_node.get_cn1_prefix() == 'SIOC:SYS0:MP01':
        self.write_epics_db(path=self.cn0_path,filename='conditions.db',template_name="cn_condition.template", macros=macros)
      elif device.card.link_node.get_cn1_prefix() == 'SIOC:SYS0:MP02':
        self.write_epics_db(path=self.cn1_path,filename='conditions.db',template_name="cn_condition.template", macros=macros)
      if device.card.link_node.get_cn2_prefix() == 'SIOC:SYS0:MP03':
        self.write_epics_db(path=self.cn2_path,filename='conditions.db',template_name="cn_condition.template", macros=macros)
    if self.verbose:
      print('........Done Export Conditions')

  def export_destinations(self,mps_db_session):
    if self.verbose:
      print('INFO: Begin Export Destinations')
    destinations = mps_db_session.query(models.BeamDestination).all()
    beamClasses = mps_db_session.query(models.BeamClass).all()
    macros = { 'NUM':'{0}'.format(len(beamClasses))}
    self.write_epics_db(path=self.cn0_path,filename='destinations.db',template_name="cn_num_beam_classes.template", macros=macros)
    self.write_epics_db(path=self.cn1_path,filename='destinations.db',template_name="cn_num_beam_classes.template", macros=macros)
    self.write_epics_db(path=self.cn2_path,filename='destinations.db',template_name="cn_num_beam_classes.template", macros=macros)
    self.bc_names.append('Full')
    for bc in beamClasses:
      self.bc_names.append(bc.name)
      macros = { 'NUM':'{0}'.format(bc.number),
                 'NAME':'{0}'.format(bc.name.upper().replace(' ','_')),
                 'DESC':'{0}'.format(bc.description),
                 'CHRG':'{0}'.format(bc.total_charge),
                 'SPACE':'{0}'.format(bc.min_period),
                 'TIME':'{0}'.format(bc.integration_window) }
      self.write_epics_db(path=self.cn0_path,filename='destinations.db',template_name="cn_beam_class_definition.template", macros=macros)
      self.write_epics_db(path=self.cn1_path,filename='destinations.db',template_name="cn_beam_class_definition.template", macros=macros)
      self.write_epics_db(path=self.cn2_path,filename='destinations.db',template_name="cn_beam_class_definition.template", macros=macros)
    for dest in destinations:
      macros = { 'DEST':'{0}'.format(dest.name.upper()),
                 'ID':'{0}'.format(dest.id) }
      self.write_epics_db(path=self.cn0_path,filename='destinations.db',template_name="cn_beam_class_destination_header.template", macros=macros)
      self.write_epics_db(path=self.cn1_path,filename='destinations.db',template_name="cn_beam_class_destination_header.template", macros=macros)
      self.write_epics_db(path=self.cn2_path,filename='destinations.db',template_name="cn_beam_class_destination_header.template", macros=macros)
      for i in range(0,len(self.bc_names)):
        macros = {"STRING":self.mbbi_strings[i],
                  "VAL":self.mbbi_vals[i],
                  "BC_NAME":self.bc_names[i],
                  "BC_VAL":"{0}".format(i)}
        self.write_epics_db(path=self.cn0_path,filename='destinations.db',template_name="cn_destination_bc_entry.template", macros=macros)
        self.write_epics_db(path=self.cn1_path,filename='destinations.db',template_name="cn_destination_bc_entry.template", macros=macros)
        self.write_epics_db(path=self.cn2_path,filename='destinations.db',template_name="cn_destination_bc_entry.template", macros=macros)
      macros = { 'DEST':'{0}'.format(dest.name.upper()),
                 'ID':'{0}'.format(dest.id) }
      self.write_epics_db(path=self.cn0_path,filename='destinations.db',template_name="cn_destination_force_bc.template", macros=macros)
      self.write_epics_db(path=self.cn1_path,filename='destinations.db',template_name="cn_destination_force_bc.template", macros=macros)
      self.write_epics_db(path=self.cn2_path,filename='destinations.db',template_name="cn_destination_force_bc.template", macros=macros)
    if self.verbose:
      print('........Done Export Destinations')

  def generate_area_displays(self,mps_db_session):
    if self.verbose:
      print("INFO: Generating area displays")
    areas = ['GUNB','L3B','DOG','LTUH','LTUS','UNDH','UNDS','DMPH','DMPS','FEEH','FEES','SPS','SPH']
    for area in areas:
      link_nodes = mps_db_session.query(models.LinkNode).filter(models.LinkNode.area == area).filter(models.LinkNode.slot_number == 2).order_by(models.LinkNode.lcls1_id).all()
      self.generate_area_display(area,link_nodes)
    #now do special case areas
    #L0B includes L0B and COL0
    link_nodes = mps_db_session.query(models.LinkNode).filter(models.LinkNode.area.in_(['L0B','COL0','HTR'])).filter(models.LinkNode.slot_number == 2).order_by(models.LinkNode.lcls1_id).all()
    self.generate_area_display('L0B',link_nodes)
    #L1B includes L1B and BC1B
    link_nodes = mps_db_session.query(models.LinkNode).filter(models.LinkNode.area.in_(['L1B','BC1B'])).filter(models.LinkNode.slot_number == 2).order_by(models.LinkNode.lcls1_id).all()
    self.generate_area_display('L1B',link_nodes)
    #L2B includes L2B and BC2B
    link_nodes = mps_db_session.query(models.LinkNode).filter(models.LinkNode.area.in_(['L2B','BC2B'])).filter(models.LinkNode.slot_number == 2).order_by(models.LinkNode.lcls1_id).all()
    self.generate_area_display('L2B',link_nodes)
    #all BPNs
    areas = ['BPN13','BPN14','BPN15','BPN16','BPN17','BPN18','BPN19','BPN20','BPN21','BPN22','BPN23','BPN24','BPN25','BPN26','BPN27','BPN28']
    link_nodes = mps_db_session.query(models.LinkNode).filter(models.LinkNode.area.in_(areas)).filter(models.LinkNode.slot_number == 2).order_by(models.LinkNode.lcls1_id).all()
    self.generate_area_display('BYP',link_nodes)
    #BSYsc
    link_nodes = mps_db_session.query(models.LinkNode).filter(models.LinkNode.area.in_(['BSYH','BSYS'])).filter(models.LinkNode.slot_number == 2).order_by(models.LinkNode.lcls1_id).all()
    self.generate_area_display('BSYsc',link_nodes)
    #BSYcu
    link_nodes = mps_db_session.query(models.LinkNode).filter(models.LinkNode.area.in_(['BSYH','BSYS','CLTS'])).filter(models.LinkNode.slot_number == 2).order_by(models.LinkNode.lcls1_id).all()
    self.generate_area_display('BSYcu',link_nodes)
    #SPD
    link_nodes = mps_db_session.query(models.LinkNode).filter(models.LinkNode.area.in_(['SPD','SLTD'])).filter(models.LinkNode.slot_number == 2).order_by(models.LinkNode.lcls1_id).all()
    self.generate_area_display('SPD',link_nodes)
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

      


