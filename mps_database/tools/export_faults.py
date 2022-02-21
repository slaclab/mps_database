#!/usr/bin/env python
from mps_database.mps_config import MPSConfig, models, runtime
from sqlalchemy import MetaData
from mps_database.tools.mps_names import MpsName
from mps_database.tools.mps_reader import MpsReader, MpsDbReader
from mps_database.tools.export_link_node import ExportLinkNode
from latex import Latex
import math
import argparse
import time
import yaml
import os
import sys

class ExportFaults(MpsReader):

  def __init__(self, db_file, template_path, dest_path,clean,verbose,report=True):
    MpsReader.__init__(self,db_file=db_file,dest_path=dest_path,template_path=template_path,clean=clean,verbose=verbose)
    self.report = report
    self.verbose = verbose
    self.mbbi_sevrs = ['ZRSV','ONSV','TWSV','THSV','FRSV','FVSV','SXSV','SVSV','EISV','NISV','TESV','ELSV','TVSV','TTSV','FTSV','FFSV']
    self.dfanout = ['OUTA','OUTB','OUTC','OUTD','OUTE','OUTF','OUTG','OUTH']
    self.letters = ['A','B','C','D','E','F','G','H','I','J','K','L']
    self.all_logic_display_macros = []
    self.ln_logic_display_macros = []
    self.cn3_logic_display_macros = []
    self.ignore_groups = []
    self.faults_for_report = []
    for i in range(0,300):
      self.ln_logic_display_macros.append([])

  def export(self,mps_db_session):
    if self.verbose:
      print("INFO: Begin Export Faults")
    self.initialize_mps_names(mps_db_session)
    self.beam_destinations = mps_db_session.query(models.BeamDestination).all()
    self.num_dest = len(self.beam_destinations)
    faults = mps_db_session.query(models.Fault).all()
    conditions = mps_db_session.query(models.Condition).all()
    for fault in faults:
      self.write_fault_db(fault)
    self.write_logic_display()
    self.writeLogicTables() 
    if self.verbose:
      print('........Done Export Faults')   


  def write_fault_db(self,fault):
    device = self.mps_names.getDeviceFromFault(fault)
    card = self.mps_names.getCardFromFault(fault)
    inputs = self.mps_names.getInputsFromDevice(device,fault)
    self.linkFaultToIgnoreGroup(device,fault,inputs)
    if card.link_node.get_cn1_prefix() == 'SIOC:SYS0:MP01':
      self.write_fault_top_db(self.cn0_path,fault,card,device,False)
      self.write_fault_state_header(self.cn0_path,fault,card,device,False)
      self.write_fault_state_header_dest(self.cn0_path,fault,card,device,False)
      self.populate_logic_display(fault,card,device,False)
      if not self.mps_names.isDeviceAnalog(device):
        self.write_fault_bypass(self.cn0_path,fault,card,device,False)
    elif card.link_node.get_cn1_prefix() == 'SIOC:SYS0:MP02':
      self.write_fault_top_db(self.cn1_path,fault,card,device,False)
      self.write_fault_state_header(self.cn1_path,fault,card,device,False)
      self.write_fault_state_header_dest(self.cn1_path,fault,card,device,False)
      self.populate_logic_display(fault,card,device,False)
      if not self.mps_names.isDeviceAnalog(device):
        self.write_fault_bypass(self.cn1_path,fault,card,device,False)
    if card.link_node.get_cn2_prefix() == 'SIOC:SYS0:MP03':
      self.write_fault_top_db(self.cn2_path,fault,card,device,True)
      self.write_fault_state_header(self.cn2_path,fault,card,device,True)
      self.write_fault_state_header_dest(self.cn2_path,fault,card,device,True)
      self.populate_logic_display(fault,card,device,True)
      if not self.mps_names.isDeviceAnalog(device):
        self.write_fault_bypass(self.cn2_path,fault,card,device,True)
    self.state_count = 0
    if self.mps_names.isDeviceAnalog(device):
      if len(fault.states) > 0:
        if card.link_node.get_cn1_prefix() == 'SIOC:SYS0:MP01':
          self.write_analog_special_case(self.cn0_path)
          self.write_analog_special_case_dest(self.cn0_path)
        elif card.link_node.get_cn1_prefix() == 'SIOC:SYS0:MP02':
          self.write_analog_special_case(self.cn1_path)
          self.write_analog_special_case_dest(self.cn1_path)
        if card.link_node.get_cn2_prefix() == 'SIOC:SYS0:MP03':
          self.write_analog_special_case(self.cn2_path)
          self.write_analog_special_case_dest(self.cn2_path)
        self.state_count += 1
    for state in fault.states:
      if card.link_node.get_cn1_prefix() == 'SIOC:SYS0:MP01':
        self.write_fault_state_entry(self.cn0_path,device,state,False)
        self.write_fault_state_entry_dest(self.cn0_path,device,state,False)
        if not self.mps_names.isDeviceAnalog(device):
          self.write_fault_state_entry(self.cn0_path,device,state,False,None,'fault_bypass.db')
      elif card.link_node.get_cn1_prefix() == 'SIOC:SYS0:MP02':
        self.write_fault_state_entry(self.cn1_path,device,state,False)
        self.write_fault_state_entry_dest(self.cn1_path,device,state,True)
        if not self.mps_names.isDeviceAnalog(device):
          self.write_fault_state_entry(self.cn1_path,device,state,False,None,'fault_bypass.db')
      if card.link_node.get_cn2_prefix() == 'SIOC:SYS0:MP03':
        self.write_fault_state_entry(self.cn2_path,device,state,True) 
        self.write_fault_state_entry_dest(self.cn2_path,device,state,True)
        if not self.mps_names.isDeviceAnalog(device):
          self.write_fault_state_entry(self.cn2_path,device,state,True,None,'fault_bypass.db')
      self.state_count += 1
    if card.link_node.get_cn1_prefix() == 'SIOC:SYS0:MP01':
      self.write_fault_state_end(self.cn0_path)
      self.write_fault_state_end_dest(self.cn0_path)
      if not self.mps_names.isDeviceAnalog(device):
        self.write_fault_state_end(self.cn0_path,'fault_bypass.db')
        self.write_input_bypass_db(self.cn0_path,device,fault,inputs,False)
    elif card.link_node.get_cn1_prefix() == 'SIOC:SYS0:MP02':
      self.write_fault_state_end(self.cn1_path)
      self.write_fault_state_end_dest(self.cn1_path)
      if not self.mps_names.isDeviceAnalog(device):
        self.write_fault_state_end(self.cn1_path,'fault_bypass.db')   
        self.write_input_bypass_db(self.cn1_path,device,fault,inputs,False)  
    if card.link_node.get_cn2_prefix() == 'SIOC:SYS0:MP03':
      self.write_fault_state_end(self.cn2_path)
      self.write_fault_state_end_dest(self.cn2_path)
      if not self.mps_names.isDeviceAnalog(device):
        self.write_fault_state_end(self.cn2_path,'fault_bypass.db') 
        self.write_input_bypass_db(self.cn2_path,device,fault,inputs,True)

  def write_fault_top_db(self,path,fault,card,device,exchange):
    name = '{0}:{1}'.format(self.mps_names.getDeviceName(device),fault.name)
    if exchange:
      name = self.exchange(name)
    if self.mps_names.isDeviceAnalog(device):
      p = '{0}{1}'.format(name,'_SCMPSC')
    else:
      p = '{0}{1}{2}'.format(name,'_FLT','_SCMPSC')
    macros = { 'NAME':'{0}{1}'.format(name,'_FLT'),
               'DESC':'{0}'.format(fault.description[:15]),
               'ID':'{0}'.format(fault.id),
               'SHIFT':'{0}'.format(fault.get_shift()),
               'FLNK':p}
    self.write_epics_db(path=path, filename='faults.db', template_name="cn_fault.template", macros=macros)

  def write_fault_state_header_dest(self,path,fault,card,device,exchange):
    self.dest_count = 1
    for dest in self.beam_destinations:
      self.write_fault_state_header(path,fault,card,device,exchange,dest)
      self.dest_count += 1

  def write_fault_state_header(self,path,fault,card,device,exchange,dest=None):
    name = '{0}:{1}'.format(self.mps_names.getDeviceName(device),fault.name)
    if exchange:
      name = self.exchange(name)
    if dest is None:
      filename = "faults.db"
      flnk = '{0}{1}_{2}_STATE'.format(name,'_FLT',self.beam_destinations[0].name.upper())
      if self.mps_names.isDeviceAnalog(device):
        p = '{0}{1}'.format(name,'_SCMPSC')
        inp = '{0}_FLT_CALC'.format(name)
        dtyp = 'Raw Soft Channel'
      else:
        p = '{0}{1}{2}'.format(name,'_FLT','_SCMPSC')
        inp = '{0}_FLT_INP'.format(name)
        dtyp = 'Raw Soft Channel'
    else:
      filename = "faults_{0}.db".format(dest.name.lower())
      p = '{0}{1}_{2}_STATE'.format(name,'_FLT',dest.name.upper(),'_SCMPSC')
      if self.dest_count < self.num_dest:
        flnk = '{0}{1}_{2}_STATE'.format(name,'_FLT',self.beam_destinations[self.dest_count].name.upper())
      else:
        flnk = ''
      if self.mps_names.isDeviceAnalog(device):
        inp = '{0}_FLT_CALC'.format(name)
        dtyp = 'Raw Soft Channel'
      else:
        inp = '{0}_FLT_INP'.format(name)
        dtyp = 'Raw Soft Channel'
    alias = '{0}{1}{2}'.format(name,'_FLT','_SCMPSC')
    macros = { 'P':p,
               'DESC':'{0}'.format(fault.description[:15]),
               'ID':'{0}'.format(fault.id),
               'INP':'{0}'.format(inp),
               'DTYP':dtyp,
               'FLNK':'{0}'.format(flnk)}
    self.write_epics_db(path=path, filename=filename, template_name="cn_mbbi_header.template", macros=macros)
    if self.mps_names.isDeviceAnalog(device) and dest is None:
      self.write_epics_db(path=path, filename='faults.db', template_name="cn_mbbi_alias.template", macros={'ALIAS':alias})

  def write_fault_state_entry_dest(self,path,device,state,exchange):
    for dest in self.beam_destinations:
      self.write_fault_state_entry(path,device,state,exchange,dest)

  def write_fault_state_entry(self,path,device,state,exchange,dest=None,file=None):
    sevr = 'NO_ALARM'
    if self.mps_names.isDeviceAnalog(device):
      val = '{0}'.format(self.state_count)
    else:
      val = '{0}'.format(state.device_state.value)
    if dest is None:
      if file is None:
        filename = "faults.db"
      else:
        filename = file
      str = state.device_state.description
    else:
      filename = "faults_{0}.db".format(dest.name.lower())
      ac = state.get_allowed_class(dest)
      if ac not in ['-']:
        str = '{0}'.format(ac.beam_class.name)
        sevr = self.mps_names.get_beam_class_severity(ac.beam_class)
      else:
        str = ac
    macros = { 'STRING':self.mbbi_strings[self.state_count],
               'VAL':self.mbbi_vals[self.state_count],
               'SEVR':self.mbbi_sevrs[self.state_count],
               'STR':str,
               'V':val,
               'SEV':sevr}
    self.write_epics_db(path=path, filename=filename, template_name="cn_mbbi_entry.template", macros=macros)

  def write_analog_special_case_dest(self,path):
    for dest in self.beam_destinations:
      self.write_analog_special_case(path,dest)

  def write_analog_special_case(self,path,dest=None):
    if dest is None:
      str = 'OK'
      filename = 'faults.db'
    else:
      filename = "faults_{0}.db".format(dest.name.lower())
      str = '-'
    macros = { 'STRING':self.mbbi_strings[self.state_count],
               'VAL':self.mbbi_vals[self.state_count],
               'SEVR':self.mbbi_sevrs[self.state_count],
               'STR':str,
               'V':'{0}'.format(self.state_count),
               'SEV':'NO_ALARM'}
    self.write_epics_db(path=path, filename=filename, template_name="cn_mbbi_entry.template", macros=macros)

  def write_fault_state_end_dest(self,path):
    for dest in self.beam_destinations:
      file = "faults_{0}.db".format(dest.name.lower())
      self.write_fault_state_end(path,file)

  def write_fault_state_end(self,path,dest=None):
    if dest is None:
      filename = 'faults.db'
    else:
      filename=dest
    self.write_epics_db(path=path, filename=filename,template_name="cn_mbbi_finish.template",macros={})

  def write_fault_bypass(self,path,fault,card,device,exchange):
    name = '{0}:{1}'.format(self.mps_names.getDeviceName(device),fault.name)
    if exchange:
      name = self.exchange(name)
    macros = { 'P':"{0}{1}".format(name,'_FLT'),
               'DESC':'{0}'.format(fault.description[:15]),
               'DTYP':'Raw Soft Channel',
               'FLNK': "",
               'OUT':'{0}{1}'.format(name,'_FLT_SCBYPV_PROC')}
    self.write_epics_db(path=path, filename="fault_bypass.db",template_name="cn_fault_byp_mbbiDirect.template",macros=macros)
    self.write_epics_db(path=path, filename="fault_bypass.db",template_name="cn_fault_bypass_mbbo.template",macros=macros)

  def write_input_bypass_db(self,path,device,fault,inputs,exchange):
    name = '{0}:{1}'.format(self.mps_names.getDeviceName(device),fault.name)
    if exchange:
      name=self.exchange(name)
    macros = {'P':'{0}{1}'.format(name,'_FLT')}
    self.write_epics_db(path=path, filename="fault_bypass.db",template_name="cn_fault_bypd.template",macros=macros)
    bit = 0
    for input in inputs:
      if exchange:
        input = self.exchange(input)
      macros = {'P':'{0}{1}'.format(name,'_FLT'),
                'OUTPV':input,
                'B':'{0}'.format(bit)}
      self.write_epics_db(path=path, filename="faults.db",template_name="cn_fault_bypass_device.template",macros=macros)
      if bit == 0:
        self.write_epics_db(path=path, filename="faults.db",template_name="cn_digital_fault_bypass_alias.template",macros=macros)
      macros = {'OUT':self.dfanout[bit],
                'VALUE':input}
      self.write_epics_db(path=path, filename="fault_bypass.db",template_name="cn_fault_bypd_entry.template",macros=macros)
      bit += 1
    self.write_epics_db(path=path, filename="fault_bypass.db",template_name="cn_mbbi_finish.template",macros={})

  def populate_logic_display(self,fault,card,device,exchange):
    name = '{0}:{1}'.format(self.mps_names.getDeviceName(device),fault.name)
    if exchange:
      name = self.exchange(name)
    macros = {}
    macros['DESCRIPTION'] = fault.description
    macros['FLT'] = '{0}{1}'.format(name,'_FLT')
    macros['VIS'] = '{0}'.format(self.mps_names.isDeviceAnalog(device))
    if exchange:
      self.cn3_logic_display_macros.append(macros)
    else:
      self.all_logic_display_macros.append(macros)
      self.ln_logic_display_macros[int(card.link_node.lcls1_id)].append(macros)

  def write_logic_display(self):
    for ln in range(2,256):
      if len(self.ln_logic_display_macros[ln]) > 0:
        filename = '{0}logic/ln{1}_logic.json'.format(self.display_path,ln)
        self.write_json_file(filename, self.ln_logic_display_macros[ln])
    filename = '{0}logic/all_logic.json'.format(self.display_path)
    self.write_json_file(filename, self.all_logic_display_macros)
    if len(self.cn3_logic_display_macros) > 0:
      filename = '{0}logic/cn3_logic.json'.format(self.display_path)
      self.write_json_file(filename, self.cn3_logic_display_macros)

  def linkFaultToIgnoreGroup(self,device,fault,inputs):
    flt_data = {}
    flt_data['fault'] = fault
    flt_data['device'] = device
    flt_data['inputs'] = inputs
    flt_data['ignore_condition'] = []
    ignore_group = []
    if len(device.ignore_conditions) > 0:
      for ic in device.ignore_conditions:
        ignore_group.append(ic.condition.id)
        flt_data['ignore_condition'].append(ic.condition.id)
      ignore_group.sort()
      if ignore_group not in self.ignore_groups:
        self.ignore_groups.append(ignore_group)
      flt_data['ignore_group'] = ignore_group
    else:
      flt_data['ignore_group'] = None
    self.faults_for_report.append(flt_data)    

  def writeLogicTables(self):
    typ = 'logic'
    filename = '{0}/SCMPS_{1}_LogicTables.tex'.format(self.report_path,self.config_version)
    self.latex = Latex(filename)
    self.latex.startDocument('SCMPS Logic Tables',self.config_version)
    faults = self.faults_for_report
    # Part of an ignore group
    for g in self.ignore_groups:
      title = 'Ignored when '
      for element in g:
        title += self.mps_names.getConditionNameFromID(element)
        if element != g[-1]:
          title += ', '
      self.latex.startIgnoreGroup(title)
      for fault in faults:
        if fault['ignore_group'] == g:
          self.latex.startFault(fault['fault'].description.replace('_','\_'))
          [format, header, rows, inputs] = self.__build_fault_table(fault)
          self.latex.writeLogicTable(format,header,rows,inputs)
    # Alywas Evaluated
    title = 'Always Evaluated'
    self.latex.startIgnoreGroup(title)
    for fault in faults:
      if fault['ignore_group'] == None:
        self.latex.startFault(fault['fault'].description.replace('_','\_'))
        [format, header, rows, inputs] = self.__build_fault_table(fault)
        self.latex.writeLogicTable(format,header,rows,inputs)
    if self.report:
      self.latex.endDocument(self.report_path)

  def __build_fault_table(self, fault):
    number_of_columns = 5 + len(fault['inputs'])
    format = '\\begin{tabular}{@{}l'
    for i in range(1,number_of_columns):
      format += 'c'
    format += '@{}}\n'
    header = 'Name & '
    inputs = []
    for inp in range(0,len(fault['inputs'])):
      header += self.letters[len(fault['inputs'])-inp-1]
      header += ' & '
      in_str = '${0} = {1}{2}{3}'.format(self.letters[inp],'\\texttt{',fault['inputs'][inp].replace('_','\_'),'}$\\newline\n')
      inputs.append(in_str)
    header += 'LINAC & DIAG0 & HXR & SXR \\\\\n'
    rows = []
    for state in fault['fault'].states:
      row = '{0} & '.format(state.device_state.description.replace('_','\_'))
      if not self.mps_names.isDeviceAnalog(fault['device']):
        val = bin(state.device_state.value)[2:].zfill(len(fault['inputs']))
        for inp in range(0,len(fault['inputs'])):
          if val[inp] == '1':
            row += 'T'
          else:
            row += 'F'
          row += ' & '
      else:
        row += 'T & '
      row += state.get_allowed_class_string_by_dest_name('LINAC') + ' & '
      row += state.get_allowed_class_string_by_dest_name('DIAG0') + ' & '
      row += state.get_allowed_class_string_by_dest_name('HXU') + ' & '
      row += state.get_allowed_class_string_by_dest_name('SXU') + ' \\\\\n'
      rows.append(row)
    return [format, header, rows, inputs]
