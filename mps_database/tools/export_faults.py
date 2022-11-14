#!/usr/bin/env python
from mps_database.mps_config import MPSConfig, models, runtime
from sqlalchemy import MetaData
from mps_database.tools.mps_names import MpsName
from mps_database.tools.mps_reader import MpsReader, MpsDbReader
from latex import Latex
import math
import argparse
import time
import yaml
import os
import sys

class ExportFaults(MpsReader):

  def __init__(self, db_file, template_path,dest_path,clean,verbose,session):
    MpsReader.__init__(self,db_file=db_file,dest_path=dest_path,template_path=template_path,clean=clean,verbose=verbose)
    self.verbose = verbose
    self.mps_names = MpsName(session)
    self.mbbi_sevrs = ['ZRSV','ONSV','TWSV','THSV','FRSV','FVSV','SXSV','SVSV','EISV','NISV','TESV','ELSV','TVSV','TTSV','FTSV','FFSV']
    self.dfanout = ['OUTA','OUTB','OUTC','OUTD','OUTE','OUTF','OUTG','OUTH']
    self.letters = ['A','B','C','D','E','F','G','H','I','J','K','L']
    self.ignore_groups = []
    self.faults_for_report = []

  def export_fault_epics(self,fault):
    if self.verbose:
      print("INFO: Working on Fault: {0}".format(fault.description))
    device = self.mps_names.getDeviceFromFault(fault)
    card = self.mps_names.getCardFromFault(fault)
    path = self.get_cn_path(card.link_node)
    inputs = self.mps_names.getInputsFromDevice(device,fault)
    name = self.mps_names.getBaseFaultName(fault)
    macros = { 'NAME':'{0}{1}'.format(name,'_FLT'),
               'DESC':'{0}'.format(fault.description[:15]),
               'ID':'{0}'.format(fault.id),
               'SHIFT':'{0}'.format(fault.get_shift())}
    self.write_template(path=path,filename='faults.db',template="cn_fault.template", macros=macros,type='central_node')
    if not self.mps_names.isDeviceAnalog(device):
      self.write_fault_bypass(fault,card,device)
      self.state_count = 0
      for state in fault.states:
        self.write_fault_state_entry(card,device,state)
        self.state_count += 1
      self.write_template(path=path,filename='fault_bypass.db',template="cn_mbbi_finish.template", macros=macros,type='central_node')
      self.write_input_bypass_db(self.get_cn_path(card.link_node),device,fault,inputs)

  def link_fault_to_ignore_group(self,fault,ignore_groups,report_faults):
    device = self.mps_names.getDeviceFromFault(fault)
    inputs = self.mps_names.getInputsFromDevice(device,fault) 
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
      if ignore_group not in ignore_groups:
        ignore_groups.append(ignore_group)
      flt_data['ignore_group'] = ignore_group
    else:
      flt_data['ignore_group'] = None
    report_faults.append(flt_data)

  def writeLogicTables(self,faults,ignore_groups,report):
    # Part of an ignore group
    for g in ignore_groups:
      title = 'Ignored when '
      for element in g:
        title += self.mps_names.getConditionNameFromID(element)
        if element != g[-1]:
          title += ', '
      report.startIgnoreGroup(title)
      for fault in faults:
        if fault['ignore_group'] == g:
          report.startFault(fault['fault'].description.replace('_','\_').replace('%','\%'))
          [format, header, rows, inputs] = self.__build_fault_table(fault)
          report.writeLogicTable(format,header,rows,inputs)
    # Alywas Evaluated
    title = 'Always Evaluated'
    report.startIgnoreGroup(title)
    for fault in faults:
      if fault['ignore_group'] == None:
        report.startFault(fault['fault'].description.replace('_','\_'))
        [format, header, rows, inputs] = self.__build_fault_table(fault)
        report.writeLogicTable(format,header,rows,inputs)  

  def write_input_bypass_db(self,path,device,fault,inputs):
    name = self.mps_names.getBaseFaultName(fault)
    macros = {'P':'{0}{1}'.format(name,'_FLT')}
    self.write_template(path=path,filename='fault_bypass.db',template="cn_fault_bypd.template", macros=macros,type='central_node')
    bit = 0
    for input in inputs:
      macros = {'OUT':self.dfanout[bit],
                'VALUE':input}
      self.write_template(path=path,filename='fault_bypass.db',template="cn_fault_bypd_entry.template", macros=macros,type='central_node')
      bit += 1
    self.write_template(path=path,filename='fault_bypass.db',template="cn_mbbi_finish.template", macros=macros,type='central_node')
    bit = 0
    for input in inputs:
      macros = {'P':'{0}{1}'.format(name,'_FLT'),
                'OUTPV':input,
                'B':'{0}'.format(bit)}
      self.write_template(path=path,filename='fault_bypass.db',template="cn_fault_bypass_device.template", macros=macros,type='central_node') #maybe faults.db
      if bit == 0:
        self.write_template(path=path,filename='fault_bypass.db',template="cn_digital_fault_bypass_alias.template", macros=macros,type='central_node')
      bit += 1
      
  def startReport(self,title):
    report = Latex(self.logic_filename)
    report.startDocument(title,self.config_version)
    return report

  def write_fault_bypass(self,fault,card,device):
    path = self.get_cn_path(card.link_node)
    name = self.mps_names.getBaseFaultName(fault)
    macros = { 'P':"{0}{1}".format(name,'_FLT'),
               'DESC':'{0}'.format(fault.description[:15]),
               'DTYP':'Raw Soft Channel',
               'FLNK': "",
               'OUT':'{0}{1}'.format(name,'_FLT_SCBYPV_PROC')}
    self.write_template(path=path,filename='fault_bypass.db',template="cn_fault_byp_mbbiDirect.template", macros=macros,type='central_node')
    self.write_template(path=path,filename='fault_bypass.db',template="cn_fault_bypass_mbbo.template", macros=macros,type='central_node')

  def write_fault_state_entry(self,card,device,state):
    path = self.get_cn_path(card.link_node)
    sevr = 'NO_ALARM'
    val = '{0}'.format(state.device_state.value)
    str = state.device_state.description
    macros = { 'STRING':self.mbbi_strings[self.state_count],
               'VAL':self.mbbi_vals[self.state_count],
               'SEVR':self.mbbi_sevrs[self.state_count],
               'STR':str,
               'V':val,
               'SEV':sevr}
    self.write_template(path=path,filename='fault_bypass.db',template="cn_mbbi_entry.template", macros=macros,type='central_node')
    
  def __build_fault_table(self, fault):
    number_of_columns = 8 + len(fault['inputs'])
    format = '\\begin{tabular}{@{}l'
    for i in range(1,number_of_columns):
      format += 'c'
    format += '@{}}\n'
    header = 'Name & '
    inputs = []
    for inp in range(0,len(fault['inputs'])):
      header += self.letters[len(fault['inputs'])-inp-1]
      header += ' & '
      in_str = '${0} = {1}{2}{3}'.format(self.letters[inp],'\\texttt{',fault['inputs'][inp].replace('_','\_').replace('&','\&'),'}$\\newline\n')
      inputs.append(in_str)
    header += 'LASER & SC\_DIAG0 & SC\_BSYD & SC\_HXR & SC\_SXR & SC\_LESA & LASER\_HTR \\\\\n'
    rows = []
    for state in fault['fault'].states:
      row = '{0} & '.format(state.device_state.description.replace('_','\_').replace('&','\&'))
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
      row += state.get_allowed_class_string_by_dest_name('LASER').replace('%','\%') + ' & '
      row += state.get_allowed_class_string_by_dest_name('SC_DIAG0').replace('%','\%') + ' & '
      row += state.get_allowed_class_string_by_dest_name('SC_BSYD').replace('%','\%') + ' & '
      row += state.get_allowed_class_string_by_dest_name('SC_HXR').replace('%','\%') + ' & '
      row += state.get_allowed_class_string_by_dest_name('SC_SXR').replace('%','\%') + ' & '
      row += state.get_allowed_class_string_by_dest_name('SC_LESA').replace('%','\%') + ' &'
      row += state.get_allowed_class_string_by_dest_name('LASER_HTR').replace('%','\%') + ' \\\\\n'
      rows.append(row)
    return [format, header, rows, inputs]

  def endReport(self,report):
    report.endDocument(self.report_path)  
