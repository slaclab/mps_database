#!/usr/bin/env python
from mps_database.mps_config import MPSConfig,models
from sqlalchemy import MetaData
import yaml
from yaml import MappingNode, ScalarNode
from sqlalchemy import Column, Integer, Float, String, Boolean
from mps_database.tools.export_report import ExportReport
import os

class ExportLogicReport(ExportReport):

  def __init__(self,session,tools,st_dest,version,verbose=False):
    ExportReport.__init__(self,session,tools,st_dest,version,verbose)
    self.filename = 'SCMPS_{0}_LogicTables.tex'.format(self.ver)
    self.letters = ['A','B','C','D','E','F','G','H','I','J','K','L']
    self.outname = 'logic_report.out'

  def export(self,lnin=-1):
    if self.v:
      print("Begin ExportLogicReport")
    self.startDocument("SCMPS Logic Tables")
    faults = self.s.query(models.Fault).order_by(models.Fault.name).all()
    destinations = self.s.query(models.BeamDestination).order_by(models.BeamDestination.display_order).all()
    igs = {}
    rf = {}
    count = 0
    for f in faults:
      ignore_group = f.get_ignore_group()
      if ignore_group not in igs.values():
        igs[count] = ignore_group
        rf[count] = []
        count = count + 1
      position = list(igs.values()).index(ignore_group)
      rf[position].append(f)
    sum = 0
    for key in igs.keys():
      ig = igs[key]
      if self.v:
        print("  Working on Ignore Group: {0}".format(ig))
      ig_faults = rf[key]
      if 'Always Evaluated' in ig:
        title = "Always Evaluated"
      else:
        tlist = ', '.join(ig)
        title = "Ignore when {0}".format(tlist)
      self.t.write_template(path=self.d,filename=self.filename,template="new_section.template",macros={"TITLE":title},type='latex')
      for f in ig_faults:
        macros = {}
        macros['TITLE'] = f.name.replace('_','\_').replace('%','\%')
        number_of_columns = 8+len(f.fault_inputs)
        format = ''
        for i in range(1,number_of_columns):
          format += 'c'
        macros['FORMAT'] = format
        header = ''
        inputs = {}
        for i in range(0,len(f.fault_inputs)):
          header += self.letters[len(f.fault_inputs)-i-1]
          header += ' & '
          inputs[self.letters[i]] = f.fault_inputs[i].channel.name.replace('_','\_').replace('&','\&')
        macros['HEADER'] = header
        self.t.write_template(path=self.d,filename=self.filename,template="new_fault_table.template",macros=macros,type='latex')
        for s in f.fault_states:
          row = '{0} & '.format(s.name.replace('_','\_').replace('&','\&'))
          val = bin(s.value)[2:].zfill(len(f.fault_inputs))
          for i in range(0,len(f.fault_inputs)):
            if val[i] == '1':
              row += 'T'
            else:
              row += 'F'
            row += ' & '
          mit = s.get_beam_classes()
          row += mit['MECH_SHUTTER'].get_name(report=True) + ' & '
          row += mit['SC_BSYD'].get_name(report=True) + ' & '
          row += mit['SC_DIAG0'].get_name(report=True) + ' & '
          row += mit['SC_HXR'].get_name(report=True) + ' & '
          row += mit['SC_SXR'].get_name(report=True) + ' & '
          row += mit['SC_LESA'].get_name(report=True) + ' & '
          row += mit['LASER_HTR'].get_name(report=True)
          macros = {}
          macros['ROW'] = row
          self.t.write_template(path=self.d,filename=self.filename,template="logic_row.template",macros=macros,type='latex')
        self.t.write_template(path=self.d,filename=self.filename,template="end_logic_table.template",macros=macros,type='latex')
        for let in inputs.keys():
          macros = {}
          macros['LETTER'] = let
          macros['INPUT'] = inputs[let]
          self.t.write_template(path=self.d,filename=self.filename,template="logic_input.template",macros=macros,type='latex')
        self.t.write_template(path=self.d,filename=self.filename,template="end_table.template",macros={},type='latex')



      
    self.endDocument()
    if self.v:
      print("End ExportLogicReport")


