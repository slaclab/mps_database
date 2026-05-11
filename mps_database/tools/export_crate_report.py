#!/usr/bin/env python
from mps_database.mps_config import MPSConfig,models
from sqlalchemy import MetaData
import yaml
from yaml import MappingNode, ScalarNode
from sqlalchemy import Column, Integer, Float, String, Boolean
from mps_database.tools.export_report import ExportReport
import os

class ExportCrateReport(ExportReport):

  def __init__(self,session,tools,st_dest,version,verbose=False):
    ExportReport.__init__(self,session,tools,st_dest,version,verbose)
    self.filename = 'SCMPS_{0}_CrateProfiles.tex'.format(self.ver)
    self.is_first = False
    self.is_right = False
    self.is_below = False
    self.first_chain = True
    self.split_ln_location = ""
    self.max_height = 3
    self.split_key = ""
    self.outname = 'crate_report.out'

  def export(self,g=-1):
    if self.v:
      print("Begin ExportCrateReport")
    self.startDocument("SCMPS Crate Profiles")
    if g > -1:
      group = self.s.query(models.LinkNodeGroup).filter(models.LinkNodeGroup.number==g).one()
      self.__crate_profile_group(group)
    else:
      groups = self.s.query(models.LinkNodeGroup).order_by(models.LinkNodeGroup.number).all()
      for group in groups:
        self.__crate_profile_group(group)
    self.endDocument()
    if self.v:
      print("End ExportCrateReport")

  def __crate_profile_group(self,g):
    if self.v:
      print("  Working on group {0}...".format(g.number))
    self.t.write_template(path=self.d,filename=self.filename,template="new_section_ticz.template",macros={"TITLE":"Link Node Group {0}".format(g.number)},type='latex')
    first_link_nodes = g.find_first_lns()
    cn = g.get_central_node()
    if len(first_link_nodes) > 1:
      # Build chains all on left or right until the split point
      split_lns = g.find_split_lns()
      if len(split_lns) > 1:
        print("ERROR: SW needs an update")
      else:
        len0 = g.build_ln_chain(first_link_nodes[0])['length']
        len1 = g.build_ln_chain(first_link_nodes[1])['length']-1
        if len0 > self.max_height:
          self.split_key = "{0}".format(self.max_height-len1)
          self.split_arrow = True
        else:
          self.split_key = "{0}".format(len0-len1+1)
          self.split_arrow = False
        self.split_ln_location = split_lns[0].crate.location
        self.is_right = False
        self.first_chain = True
        split_ln = 0
        for fln in first_link_nodes:
          self.is_first = True
          self.is_below = False
          last_ln = self.__build_chain(g,fln,False,split_ln)
          self.first_chain = False
          self.is_right = True
          split_ln = last_ln
        self.__add_central_node(split_lns[0],cn)
    else:
      # Build chain from top left to bottom right
      first_ln = first_link_nodes[0]
      self.is_first = True
      self.is_right = False
      self.is_below = False
      last_ln = self.__build_chain(g,first_link_nodes[0])
      self.__add_central_node(last_ln,cn)
    self.t.write_template(path=self.d,filename=self.filename,template="end_section.template",macros={},type='latex')

  def __build_chain(self,group,first_ln,increment=True,last_ln=0):
    count = 1
    chain = group.build_ln_chain(first_ln)
    for c in range(chain['length']):
      if not increment and count > self.max_height:
        self.is_right = True
        self.is_below = False
      key = "{0}".format(c+1)
      macros = self.crate_profile(chain[key])
      instructions = self.__get_instruction(last_ln,chain[key])
      macros["INST"] = instructions[0]       
      macros["ARROW"] = instructions[1]
      if chain[key].crate.location != self.split_ln_location or self.first_chain:
        self.t.write_template(path=self.d,filename=self.filename,template="link_node.template",macros=macros,type='latex')
        if not self.is_first:
          self.t.write_template(path=self.d,filename=self.filename,template="arrow.template",macros=macros,type='latex')
      else:
        self.is_below = self.split_arrow
        instructions = self.__get_instruction(last_ln,chain[key])
        macros['INST'] = instructions[0]
        macros["ARROW"] = instructions[1]
        self.t.write_template(path=self.d,filename=self.filename,template="arrow.template",macros=macros,type='latex')
      count = count + 1
      last_ln = chain[key]
      if increment:
        self.__increment_ln()
      else:
        self.is_first = False
        self.is_below = True
    if not increment:
      last_ln = chain[self.split_key]
    return last_ln

  def __add_central_node(self,last_ln,cn):
    props = cn.get_cn_properties()
    macros = {}
    macros["ID"] = "LN{0}".format(props['cnid'])
    macros["CNID"] = "{0}".format(props["cnid"])
    macros["LOCATION"] = props["crate"]
    macros["SHM"] = props["shm"]
    instructions = self.__get_cn_instructions(last_ln,cn)
    macros["INST"] = instructions[0]
    macros["ARROW"] = instructions[1]
    self.t.write_template(path=self.d,filename=self.filename,template="central_node.template",macros=macros,type='latex')
    self.t.write_template(path=self.d,filename=self.filename,template="arrow.template",macros=macros,type='latex')

  def __get_chain_length(self,chain):
    return len(chain)

  def __increment_ln(self):
    if self.is_first:
      self.is_first = False
      self.is_right = True
      self.is_below = False
    else:
      if self.is_right and not self.is_below:
        self.is_right = True
        self.is_below = True
      elif self.is_right and self.is_below:
        self.is_right = False
        self.is_below = False
      elif not self.is_right and not self.is_below:
        self.is_right = False
        self.is_below = True
      elif not self.is_right and self.is_below:
        self.is_right = True
        self.is_below = False


  def __get_instruction(self,last_ln,ln):
    if self.is_first:
      if not self.is_right:
        return ["[linknode]",""]
      else:
        inst = "[linknode,right of=LN{0}][node distance=9cm]".format(last_ln.lnid)
        arrow = '(LN{0}) -- node[anchor=south] {{Rx {1}}} (LN{2});'.format(last_ln.lnid,last_ln.rx_pgp,ln.lnid)
        return [inst,arrow]
    else:
      if self.is_right and not self.is_below:
        inst = "[linknode,right of=LN{0}][node distance=9cm]".format(last_ln.lnid)
        arrow = '(LN{0}) -- node[anchor=south] {{Rx {1}}} (LN{2});'.format(last_ln.lnid,last_ln.rx_pgp,ln.lnid)
        return [inst,arrow]
      elif self.is_right and self.is_below:
        inst = "[linknode,below of=LN{0}][node distance=6cm]".format(last_ln.lnid)
        arrow = '(LN{0}) -- node[anchor=west] {{Rx {1}}} (LN{2});'.format(last_ln.lnid,last_ln.rx_pgp,ln.lnid)
        return [inst,arrow]
      elif not self.is_right and not self.is_below:
        inst = "[linknode,left of=LN{0}][node distance=9cm]".format(last_ln.lnid)
        arrow = '(LN{0}) -- node[anchor=south] {{Rx {1}}} (LN{2});'.format(last_ln.lnid,last_ln.rx_pgp,ln.lnid)
        return [inst,arrow]
      elif not self.is_right and self.is_below:
        inst = "[linknode,below of=LN{0}][node distance=6cm]".format(last_ln.lnid)
        arrow = '(LN{0}) -- node[anchor=west] {{Rx {1}}} (LN{2});'.format(last_ln.lnid,last_ln.rx_pgp,ln.lnid)
        return [inst,arrow]
      else:
        return "" 

  def __get_cn_instructions(self,last_ln,cn):
      inst = "[linknode,below of=LN{0}][node distance=4cm]".format(last_ln.lnid)
      arrow = '(LN{0}) -- node[anchor=west] {{Rx {1}}} (LN{2});'.format(last_ln.lnid,last_ln.rx_pgp,cn.lnid)
      return [inst,arrow]