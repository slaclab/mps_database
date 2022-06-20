#!/usr/bin/env python
from mps_database.mps_config import MPSConfig, models, runtime
from sqlalchemy import MetaData
from mps_database.tools.mps_names import MpsName
from mps_database.tools.mps_reader import MpsReader, MpsDbReader
from mps_database.tools.export_link_node import ExportLinkNode
from mps_database.tools.cn_status_display import CnStatusDisplay
from latex import Latex
import math
import argparse
import time
import yaml
import os
import sys

class ExportLinkNodeGroups(MpsReader):

  def __init__(self, db_file, template_path, dest_path,clean, verbose,report=True):
    MpsReader.__init__(self,db_file=db_file,dest_path=dest_path,template_path=template_path,clean=clean,verbose=verbose)
    self.export_ln = ExportLinkNode(db_file,template_path,dest_path,False,verbose)
    self.cn_status_display = CnStatusDisplay()
    self.report = report
    self.verbose = verbose

  def export(self,mps_db_session):
    if self.verbose:
      print("INFO: Begin Exporting Devices")
    crate_filename = '{0}/SCMPS_{1}_CrateProfiles.tex'.format(self.report_path,self.config_version)
    input_filename = '{0}/SCMPS_{1}_DeviceInputs.tex'.format(self.report_path,self.config_version)
    appendixA_filename = '{0}/SCMPS_{1}_AppendixA.tex'.format(self.report_path,self.config_version)
    appendixB_filename = '{0}/SCMPS_{1}_AppendixB.tex'.format(self.report_path,self.config_version)
    self.crate_profiles = Latex(crate_filename)
    self.crate_profiles.startDocument('SCMPS Crate Profiles',self.config_version)
    self.input_report = Latex(input_filename)
    self.input_report.startDocument('Appendix B: SCMPS Device Input Checkout',self.config_version)
    self.appendixA = Latex(appendixA_filename)
    self.appendixA.startDocument('Appendix A: SCMPS FW/SW Checkout',self.config_version)
    groups = mps_db_session.query(models.LinkNodeGroup).order_by(models.LinkNodeGroup.number).all()
    for group in groups:
      self.generate_group_alarm(group)
      self.crate_profiles.startGroup(group.number)
      if group.has_inputs():
        self.input_report.startGroup(group.number)
      self.export_ln.export(mps_db_session,group.link_nodes,self.crate_profiles,self.input_report,self.cn_status_display,self.appendixA)
      self.generate_group_display(group.number,[ln for ln in group.link_nodes if ln.slot_number == 2])
    filename = '{0}status/cn_status.json'.format(self.display_path)
    self.write_json_file(filename, self.cn_status_display.get_macros())
    if self.report:
      self.crate_profiles.endDocument(self.report_path)
      self.input_report.endDocument(self.report_path)
      self.appendixA.endDocument(self.report_path)
    if self.verbose:
      print('........Done Exporting Devices')   

  def generate_group_alarm(self,group):
    macros = {'MPS_PREFIX':group.central_node1,
              'LN_GROUP':'{0}'.format(group.number)}
    file_path1 = '{0}timeout/group_{1}_{2}.alhConfig'.format(self.alarm_path,group.number,group.central_node1.split(':')[2].lower())
    self.write_alarm_file(path=file_path1, template_name='mps_group_header.template', macros=macros)
    include_path1 = '{0}group_{1}_include.txt'.format(self.alarm_path,group.central_node1.split(':')[2].lower())
    include_macros1 = {'PREFIX':group.central_node1,
                      'FILENAME':'group_{0}_{1}.alhConfig'.format(group.number,group.central_node1.split(':')[2].lower())}
    self.write_alarm_file(path=include_path1, template_name='group_include.template', macros=include_macros1)
    if group.central_node1 != group.central_node2:
      macros = {'MPS_PREFIX':group.central_node2,
                'LN_GROUP':'{0}'.format(group.number)}
      file_path2 = '{0}timeout/group_{1}_{2}.alhConfig'.format(self.alarm_path,group.number,group.central_node2.split(':')[2].lower())
      self.write_alarm_file(path=file_path2, template_name='mps_group_header.template', macros=macros)
      include_path2 = '{0}group_{1}_include.txt'.format(self.alarm_path,group.central_node2.split(':')[2].lower())
      include_macros2 = {'PREFIX':group.central_node2,
                        'FILENAME':'group_{0}_{1}.alhConfig'.format(group.number,group.central_node2.split(':')[2].lower())}
      self.write_alarm_file(path=include_path2, template_name='group_include.template', macros=include_macros2)
    

  def generate_group_display(self,group,link_nodes):
    header_height = 50
    footer_height = 51
    embedded_width = 457
    embedded_height = 230
    extra = 10
    max_width = 2000
    fudge = 0
    last_y = header_height
    rows = 1
    number_of_nodes = len(link_nodes)
    window_width = number_of_nodes * embedded_width+extra*2
    too_long = False
    last_ln = [ln for ln in link_nodes if ln.group_link == 0]
    if len(last_ln) > 1:
      for ln in last_ln:
        print(ln.get_name())
      print("ERROR: Too many last link nodes in group {0}".format(group))
      return
    if len(last_ln) < 1:
      print("ERROR: Not enough last link nodes in group {0}".format(group))
      return
    last_ln = last_ln[0]
    next_to_last_ln = [ln for ln in link_nodes if ln.group_link == last_ln.crate.id]
    if len(next_to_last_ln) > 1:
      last_y = last_y + embedded_height/2
      rows = 2
      window_width = int((math.floor(len(link_nodes)/2)+1) * embedded_width + extra * 2)
    if window_width > max_width:
      last_y = last_y + embedded_height
      rows = 2
      too_long = True
      window_width = int((math.floor(len(link_nodes)/2)+1) * embedded_width + extra * 2)
      fudge = int(embedded_width / 2)
    window_height = header_height + footer_height + rows*embedded_height
    last_x = window_width - embedded_width - extra - fudge
    macros = { 'WIDTH':'{0}'.format(int(window_width)),
               'HEIGHT':'{0}'.format(int(window_height)),
               'TITLE':'SC Linac MPS Link Node Group {0}'.format(group) }
    filename = '{0}groups/LinkNodeGroup{1}.ui'.format(self.display_path,group)
    self.__write_group_header(path=filename,macros=macros)
    vis = "0"
    cn1 = last_ln.get_cn1_prefix()
    cn2 = last_ln.get_cn2_prefix()
    if cn1 == cn2:
      vis = "1"
    self.write_group_embed(last_ln,last_x,last_y,'REM',vis,'CN B005',cn1,cn2,filename)
    if rows > 1:
      y = header_height + embedded_height
    else:
      y = header_height
    for node in next_to_last_ln:
      test_ln = node
      pin = last_ln.get_app_prefix()
      x = last_x - embedded_width
      self.write_group_embed(node,x,y,'LOC','0','LN Rx',pin,pin,filename)
      more_lns = True
      while more_lns:
        pin = test_ln.get_app_prefix()
        lk = [ln for ln in link_nodes if ln.group_link == test_ln.crate.id]
        if len(lk) < 1:
          more_lns = False
          break
        test_ln = lk[0]
        x = x-embedded_width
        if x<0:
          if too_long:
            x = window_width - embedded_width - extra
            y = y-embedded_height
        self.write_group_embed(test_ln,x,y,'LOC','0','LN Rx',pin,pin,filename)
      y = y-embedded_height
    y = window_height-footer_height-1
    buttonx = int(window_width/2-100)
    buttony = y + 12
    macros = { 'CN':'{0}'.format(last_ln.get_cn1_prefix()),
               'BUTTON_X':'{0}'.format(int(buttonx)),
               'BUTTON_Y':'{0}'.format(int(buttony)),
               'Y':'{0}'.format(int(y)) }
    self.__write_group_end(path=filename,macros=macros)

  def write_group_embed(self,ln,x,y,type,vis,text,pin1,pin2,filename):
    macros = { 'P':'{0}'.format(ln.get_app_prefix()),
               'CN':'{0}'.format(ln.get_cn1_prefix()),
               'AID':'{0}'.format(ln.get_digital_app_id()),
               'SLOT_FILE':'LinkNode{0}_slot.ui'.format(ln.lcls1_id),
               'P_IN':'{0}'.format(pin1),
               'P_IN2':'{0}'.format(pin2),
               'X':'{0}'.format(int(x)),
               'Y':'{0}'.format(int(y)),
               'PGP':'{0}'.format(ln.group_link_destination),
               'LN':'{0}'.format(ln.lcls1_id),
               'TYPE':'{0}'.format(type),
               'LOCA':'{0}'.format(ln.area),
               'IOC_UNIT':'{0}'.format(ln.location),
               'INST':'{0}'.format(ln.get_app_number()),
               'VIS':vis,
               'TEXT':'{0}'.format(text)}
    self.__write_group_embed(path=filename,macros=macros)

  def __write_group_header(self, path, macros):
      self.write_ui_file(path=path, template_name="ln_group_header.tmpl",macros=macros)
 
  def __write_group_embed(self, path, macros):
      self.write_ui_file(path=path, template_name="link_node_group_embedded_display.tmpl",macros=macros)

  def __write_group_end(self, path, macros):
      self.write_ui_file(path=path, template_name="ln_group_end.tmpl",macros=macros)
