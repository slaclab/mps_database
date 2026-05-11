#!/usr/bin/env python
from mps_database.mps_config import MPSConfig, models
from sqlalchemy import MetaData
import yaml
from yaml import MappingNode, ScalarNode
from sqlalchemy import Column, Integer, Float, String, Boolean

class ExportCentralNode():

  def __init__(self,session,tools,st_dest,version,verbose=False):
    self.v = verbose
    self.s = session
    self.ver = version
    self.t = tools
    self.d = st_dest

  def export(self):
    if self.v:
      print("Begin ExportCentralNode")
    st_dest = '{0}/central_node/startup/'.format(self.d)
    disp_dest = '{0}/display/'.format(self.d)
    cns = self.s.query(models.CentralNode).all()
    dests = self.s.query(models.BeamDestination).all()
    for cn in cns:
      st_name = '{0}.db'.format(cn.get_ioc_name())
      for g in cn.groups:
        for ln in g.link_nodes:
          input_disp_filename = '{0}inputs/ln_{1}_inputs.json'.format(disp_dest,ln.lnid)
          input_disp_macros = []
          for app in ln.get_app_cards():
            macros = {"P":app.get_mps_prefix(),
                      "APP":"{0}".format(app.number),
                      "ID":"{0}".format(app.id),
                      "TYPE":app.type.name,
                      "LOCA":app.get_location(),
                      "ATTR":app.get_attribute()}
            self.t.write_template(st_dest,filename=st_name,template='cn_app_timeout.template',macros=macros,type='central_node')
            for ch in app.channels:
              for m in ch.get_channel_properties():
                if m["IN_CN"]:
                  del(m["IN_CN"])
                  self.t.write_template(st_dest,filename=st_name,template='cn_bypass.template',macros=m,type='central_node')
                  self.t.write_template(st_dest,filename=st_name,template='cn_channel.template',macros=m,type='central_node')
                  macros = { "CRATE":m["CRATE"],
                             "SLOT":m["SLOT"],
                             "DEVICE":m["DEVICE"],
                             "CHANNEL":m["CHANNEL"],
                             "DEVICE_BYP":m["DEVICE_BYP"],
                             "APPID":m["APPID"] }
                  input_disp_macros.append(macros)
          self.t.write_json_file(input_disp_filename,input_disp_macros)
      for ic in cn.ignore_conditions:
        macros = ic.get_condition_properties()
        self.t.write_template(st_dest,filename=st_name,template='cn_condition.template',macros=macros,type='central_node')

    faults = self.s.query(models.Fault).all()
    for f in faults:
      st_name = "{0}.db".format(f.get_central_node().get_ioc_name())
      macros = f.get_fault_properties()
      states = f.get_fault_states(bypass=True)
      # Write Fault PVs
      self.t.write_template(st_dest,filename=st_name,template='cn_fault.template',macros=macros,type='central_node')
      # Write Fault Bypass
      self.t.write_template(st_dest,filename=st_name,template='cn_bypass_state_header.template',macros=macros,type='central_node')
      self._write_fault_states(states,st_dest,st_name)
      self.t.write_template(st_dest,filename=st_name,template='cn_mbbi_finish.template',macros=macros,type='central_node')
      # Write Fault Bypass RBV
      self.t.write_template(st_dest,filename=st_name,template='cn_bypass_state_header_rbv.template',macros=macros,type='central_node')
      self._write_fault_states(states,st_dest,st_name)
      self.t.write_template(st_dest,filename=st_name,template='cn_mbbi_finish.template',macros=macros,type='central_node')
    if self.v:
      print("End ExportCentralNode")

  def _write_fault_states(self,states,dest,file):
    count = 0
    for key in states:
        macros = { "STRING":self.t.mbbi_strings[count],
                   "STR":states[key],
                   "VAL":self.t.mbbi_vals[count],
                   "V":"{0}".format(key),
                   "SEVR":self.t.mbbi_sevr[count],
                   "SEV":"NO_ALARM"}
        self.t.write_template(dest,filename=file,template='cn_mbbo_entry.template',macros=macros,type='central_node')
        count = count + 1


  