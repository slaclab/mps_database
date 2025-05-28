#!/usr/bin/env python
from mps_database.mps_config import MPSConfig, models
from sqlalchemy import MetaData
import yaml
from yaml import MappingNode, ScalarNode
from sqlalchemy import Column, Integer, Float, String, Boolean

class ExportManager():

  def __init__(self,session,tools,st_dest,version,verbose=False):
    self.v = verbose
    self.s = session
    self.ver = version
    self.t = tools
    self.d = st_dest


  def export(self):
    if self.v:
      print("Begin ExportManager")
    manager_dest = '{0}/manager/'.format(self.d)
    filename = "manager.cmd"
    lns = self.s.query(models.LinkNode).all()
    for ln in lns:
      props = ln.get_ln_properties()
      macros = {}
      macros["P"] = "{0}".format(props['p'])
      macros["GROUP"] = "{0}".format(props['group'])
      macros["CPU"] = "{0}".format(props['cpu'])
      macros["SHM"] = "{0}".format(props['shm'])
      macros["CRATE"] = "{0}".format(props['crate'])
      macros["SIOC"] = "{0}".format(props['sioc'])
      macros["S1A"] = "{0}".format(props['slot1']['app'])
      macros["S2U"] = "{0}".format(props['slot2']['used'])
      macros["S2T"] = "{0}".format(props['slot2']['short_name'])
      macros["S2A"] = "{0}".format(props['slot2']['app'])
      macros["S3U"] = "{0}".format(props['slot3']['used'])
      macros["S3T"] = "{0}".format(props['slot3']['short_name'])
      macros["S3A"] = "{0}".format(props['slot3']['app'])
      macros["S4U"] = "{0}".format(props['slot4']['used'])
      macros["S4T"] = "{0}".format(props['slot4']['short_name'])
      macros["S4A"] = "{0}".format(props['slot4']['app'])
      macros["S5U"] = "{0}".format(props['slot5']['used'])
      macros["S5T"] = "{0}".format(props['slot5']['short_name'])
      macros["S5A"] = "{0}".format(props['slot5']['app'])
      macros["S6U"] = "{0}".format(props['slot6']['used'])
      macros["S6T"] = "{0}".format(props['slot6']['short_name'])
      macros["S6A"] = "{0}".format(props['slot6']['app'])
      macros["S7U"] = "{0}".format(props['slot7']['used'])
      macros["S7T"] = "{0}".format(props['slot7']['short_name'])
      macros["S7A"] = "{0}".format(props['slot7']['app'])
      self.t.write_template(manager_dest,filename=filename,template='ln_prop.template',macros=macros,type='manager')
    channels = self.s.query(models.AnalogChannel).all()
    for chan in channels:
      macros = {'INP':chan.name}
      self.t.write_template(manager_dest,filename=filename,template='manager_thr.template',macros=macros,type='manager')
      if "I0_" in chan.name:
        inp1 = chan.name.replace("I0_","I1_")
        macros = {'INP':inp1}
        self.t.write_template(manager_dest,filename=filename,template='manager_thr.template',macros=macros,type='manager')
      if chan.name.find('CBLM') > -1:
        macros = {}
        macros['P'] = chan.card.get_mps_prefix()
        macros['DEV'] = chan.get_device_prefix()
        macros['CH'] = '{0}'.format(chan.number)
        macros['TRG'] = '{0}'.format(chan.number+10)
        macros['TPR'] = chan.card.get_tpr()
        self.t.write_template(manager_dest,filename=filename,template='manager_time_window.template',macros=macros,type='manager')
    if self.v:
      print("End ExportManager")