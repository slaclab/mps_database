#!/usr/bin/env python
from mps_database.mps_config import MPSConfig,models
from sqlalchemy import MetaData
import yaml
from yaml import MappingNode, ScalarNode
from sqlalchemy import Column, Integer, Float, String, Boolean
from mps_database.tools.export_report import ExportReport
import os

class ExportInputReport(ExportReport):

  def __init__(self,session,tools,st_dest,version,verbose=False):
    ExportReport.__init__(self,session,tools,st_dest,version,verbose)
    self.filename = 'SCMPS_{0}_DeviceInputs.tex'.format(self.ver)
    self.outname = 'input_report.out'


  def export(self,lnin=-1):
    if self.v:
      print("Begin ExportInputReport")
    self.startDocument("SCMPS Device Inputs")
    if lnin > -1:
      ln = self.s.query(models.LinkNode).filter(models.LinkNode.lnid==lnin).one()
      self.__device_input_ln(ln)
    else:
      lns = self.s.query(models.LinkNode).order_by(models.LinkNode.lnid).all()
      for ln in lns:
        self.__device_input_ln(ln)
    self.endDocument()
    if self.v:
      print("End ExportInputReport")

  def __device_input_ln(self,ln):
    if self.v:
      print("  Working on LinkNode {0}...".format(ln.lnid))
    macros = self.crate_profile(ln)
    self.t.write_template(path=self.d,filename=self.filename,template="link_node_di.template",macros=macros,type='latex')
    self.t.write_template(path=self.d,filename=self.filename,template="begin_device_input_table.template",macros=macros,type='latex')
    for card in ln.crate.cards:
      for ch in card.channels:
        macros = {}
        macros['AID'] = '{0}'.format(card.number)
        macros['SLOT'] = '{0}'.format(card.get_slot_text())
        macros['CH'] = '{0}'.format(ch.number)
        macros['NAME'] = ch.name.replace('_','\_').replace('&','\&')
        self.t.write_template(path=self.d,filename=self.filename,template="channel.template",macros=macros,type='latex')
    self.t.write_template(path=self.d,filename=self.filename,template="end_device_input_table.template",macros=macros,type='latex')

