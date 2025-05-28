#!/usr/bin/env python
from mps_database.mps_config import MPSConfig, models
from sqlalchemy import MetaData
import yaml
from yaml import MappingNode, ScalarNode
from sqlalchemy import Column, Integer, Float, String, Boolean

class ExportLinkNode():

  def __init__(self,session,tools,st_dest,version,verbose=False):
    self.v = verbose
    self.s = session
    self.ver = version
    self.t = tools
    self.d = st_dest

  def export(self):
    if self.v:
      print("Begin ExportLinkNode")
    lns = self.s.query(models.LinkNode).all()
    st_dest = '{0}/link_node/startup/'.format(self.d)
    yaml_dest = '{0}/link_node/config/'.format(self.d)
    for ln in lns:
      for card in ln.get_app_cards():
        st_name = '{0}.cmd'.format(card.get_ioc_name())
        yaml_name = '{0}.yaml'.format(card.get_ioc_name())
        if card.has_mps_ioc():    
          macros = {"VER":self.ver,
                    "PREFIX":card.get_mps_prefix(),
                    "CRATE":'{0}'.format(card.crate.get_ip_num()),
                    "SLOT":"{0}".format(card.get_real_slot()),
                    "LOC":card.crate.area,
                    "LOC_IDX":card.location,
                    "SHM":card.crate.get_nodename()}
          self.t.write_template(st_dest,filename=st_name,template='ioc_prop.template',macros=macros,type='link_node')
          if card.slot < 3:
            macros = ln.map_nc_config()
            self.t.write_template(path=yaml_dest,filename=yaml_name,template="lc1_info.template",macros=macros,type='link_node')
        if card.is_mps_digital():
          self.t.write_template(st_dest,filename=st_name,template='dig_aid.template',macros={"DAID":'{0}'.format(card.number)},type='link_node')
          if card.can_have_software():
            for chan in card.channels:
              if chan.number > 31:
                macros = {"P":card.get_mps_prefix(),
                          "INPV":chan.monitored_pv,
                          "NAME":chan.name,
                          "CH":"{:02d}".format(chan.number-32)}
                if chan.wdog:
                  self.t.write_template(st_dest,filename=st_name,template='wdog.template', macros=macros,type='link_node')
                else:
                  if 'BPMS' in chan.name:
                    self.t.write_template(st_dest,filename=st_name,template='bpm.template', macros=macros,type='link_node')
                  else:
                    self.t.write_template(st_dest,filename=st_name,template='analog.template', macros=macros,type='link_node')
        if card.is_mps_analog():
          self.t.write_template(st_dest,filename=st_name,template='app_prop.template',macros={"AID":'{0}'.format(card.number),"BAYS":'{0}'.format(card.get_bays_populated())},type='link_node')
          for chan in card.channels:
            macros = {"P":chan.get_device_prefix(),
                      "R":chan.get_device_attribute(),
                      "EGU":chan.egu,
                      "CH":'{0}'.format(chan.number)}
            self.t.write_template(st_dest,filename=st_name,template='ana_ch_prop.template',macros=macros,type='link_node')
            if chan.wf_only:
              macros = {"CH":"{0}".format(chan.number),"GC":"{0}".format(chan.gain_channel)}
              self.t.write_template(st_dest,filename=st_name,template='is_wf.template',macros=macros,type='link_node')
            else:
              self.t.write_template(st_dest,filename=st_name,template='is_mps.template',macros={"CH":"{0}".format(chan.number)},type='link_node')
              if self.t.is_lc1(card.crate.area):
                self.t.write_template(st_dest,filename=st_name,template='is_lc1_bsa.template',macros={"CH":"{0}".format(chan.number)},type='link_node')
    if self.v:
      print("End ExportLinkNode")