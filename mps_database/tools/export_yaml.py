#!/usr/bin/env python
from mps_database.mps_config import MPSConfig, models
from sqlalchemy import MetaData
import yaml
from yaml import MappingNode, ScalarNode
from sqlalchemy import Column, Integer, Float, String, Boolean


class ExportYaml():

  def __init__(self,session,tools,dest,version,verbose=False):
    self.v = verbose
    self.s = session
    self.path = dest
    self.ver = version

  def export(self):
    if self.v:
      print("INFO: Starting Export Yaml...")
    for cn in self.s.query(models.CentralNode).all():
      if self.v:
        print("  INFO: Working on CN{0}".format(cn.id))
      yaml_fn = '{0}/mps_config-cn{1}-{2}.yaml'.format(self.path,cn.id,self.ver)
      f = open(yaml_fn,"w")
      yaml.add_multi_representer(models.Base,self.model_representer)
      # Dump db parts to yaml that are common to all central nodes
      common_models = [models.ApplicationType,
                       models.BeamClass,
                       models.BeamDestination,
                       models.Mitigation]
      for model in common_models:
        collection = self.s.query(model).order_by(model.id).all()
        yaml.dump({model.__name__: collection},f,explicit_start=True)
      link_nodes = []
      crates = []
      app_cards = []
      app_ids = []
      digital_channels = []
      analog_channels = []
      ignore_conditions = []
      faults = []
      fault_inputs = []
      fault_states = []
      for g in cn.groups:
        for ln in g.link_nodes:
          link_nodes.append(ln)
          crates.append(ln.crate)
          for c in ln.crate.cards:
            app_cards.append(c)
            app_ids.append(c.id)
            for ch in c.channels:
              if ch.discriminator == 'analog_channel':
                analog_channels.append(ch)
              else:
                digital_channels.append(ch)
                if len(ch.ignore_condition) > 0:
                  if len(ch.ignore_condition) > 1:
                    print("ERROR: Too many ignore conditions!!!")
                    raise
                  ignore_conditions.append(ch.ignore_condition[0])
      link_nodes.sort(key=self.get_id)
      crates.sort(key=self.get_id)
      app_cards.sort(key=self.get_id)
      digital_channels.sort(key=self.get_id)
      analog_channels.sort(key=self.get_id)
      ignore_conditions.sort(key=self.get_id)

      fault = self.s.query(models.Fault).join(models.FaultInput,models.FaultInput.fault_id==models.Fault.id).join(models.Channel,models.Channel.id==models.FaultInput.channel_id).join(models.ApplicationCard,models.Channel.card_id==models.ApplicationCard.id).join(models.Crate,models.ApplicationCard.crate_id==models.Crate.id).join(models.LinkNode,models.LinkNode.crate_id==models.Crate.id).join(models.LinkNodeGroup,models.LinkNode.group_id==models.LinkNodeGroup.id).filter(models.LinkNodeGroup.central_node==cn).all()
      for fa in fault:
        fau = {}
        fau['id'] = fa.id
        fau['pv'] = "{0}".format(fa.pv)
        fau['name'] = "{0}".format(fa.name)
        fau['ignore_conditions'] = []
        for ic in fa.ignore_conditions:
          fau['ignore_conditions'].append(ic.id)
        faults.append(fau)
        if len(fa.fault_inputs) > 0:
          for fi in fa.fault_inputs:
            fault_inputs.append(fi)
        if len(fa.fault_states) > 0:
          for fs in fa.fault_states:
            fss = {}
            fss['id'] = fs.id
            fss['fault_id'] = fs.fault_id
            fss['default'] = fs.default
            fss['name'] = "{0}".format(fs.name)
            fss['value'] = fs.value
            fss['mask'] = fs.mask
            fss['mitigations'] = []
            if len(fs.mitigations) > 0:
              for m in fs.mitigations:
                fss['mitigations'].append(m.id)
            fss['mitigations'].sort()
            fault_states.append(fss)

      faults.sort(key=self.get_dict_id)
      fault_inputs.sort(key=self.get_id)
      fault_states.sort(key=self.get_dict_id)
      yaml.dump({models.LinkNode.__name__: link_nodes}, f, explicit_start=True)
      yaml.dump({models.Crate.__name__: crates}, f, explicit_start=True)
      yaml.dump({models.ApplicationCard.__name__: app_cards}, f, explicit_start=True)
      yaml.dump({models.DigitalChannel.__name__: digital_channels}, f, explicit_start=True)
      yaml.dump({models.AnalogChannel.__name__: analog_channels}, f, explicit_start=True)
      yaml.dump({models.IgnoreCondition.__name__: ignore_conditions}, f, explicit_start=True)
      yaml.dump({'Fault': faults}, f, explicit_start=True)
      yaml.dump({models.FaultInput.__name__: fault_inputs}, f, explicit_start=True)
      yaml.dump({'FaultState': fault_states}, f, explicit_start=True)
      f.close()
    if self.v:
      print("INFO: Starting Export Yaml...DONE!")

  #This is a pyyaml representer for any object that inherits from SQLAlchemy's declarative base class.  
  def model_representer(self,dumper, obj):
    node = MappingNode(tag='tag:yaml.org,2002:map', value=[], flow_style=False)
    for column in obj.__table__.columns:
      if isinstance(column.type, String):
        node.value.append((ScalarNode(tag='tag:yaml.org,2002:str', value=column.name), 
                           dumper.represent_scalar(tag='tag:yaml.org,2002:str', value=str(getattr(obj, column.name)), style='"')))
      elif isinstance(column.type, Integer):
        node.value.append((ScalarNode(tag='tag:yaml.org,2002:str', value=column.name), 
                           dumper.represent_scalar(tag='tag:yaml.org,2002:int', value=str(getattr(obj, column.name)), style='')))
      elif isinstance(column.type, Float):
        node.value.append((ScalarNode(tag='tag:yaml.org,2002:str', value=column.name), 
                           dumper.represent_scalar(tag='tag:yaml.org,2002:float', value=str(getattr(obj, column.name)), style='')))
      elif isinstance(column.type, Boolean):
        node.value.append((ScalarNode(tag='tag:yaml.org,2002:str', value=column.name), 
                           dumper.represent_scalar(tag='tag:yaml.org,2002:bool', value=str(getattr(obj, column.name)), style='')))
      else:
        raise TypeError("No scalar representation is implemented for SQLAlchemy column type {col_type}".format(column.type))
    # This code is to print out the attributes inherited from the class Device by the AnalogDevice and DigitalDevice
    if (hasattr(obj.__class__.__bases__[0],'__tablename__')):
      if (obj.__class__.__bases__[0].__tablename__ == "channels"):
        for column in obj.__class__.__bases__[0].__table__.columns:
          if (column.name != 'type' and column.name != 'id'):
            if isinstance(column.type, String):
              node.value.append((ScalarNode(tag='tag:yaml.org,2002:str', value=column.name), 
                                 dumper.represent_scalar(tag='tag:yaml.org,2002:str', value=str(getattr(obj, column.name)), style='"')))
            elif isinstance(column.type, Integer):
              node.value.append((ScalarNode(tag='tag:yaml.org,2002:str', value=column.name), 
                                 dumper.represent_scalar(tag='tag:yaml.org,2002:int', value=str(getattr(obj, column.name)), style='')))
            elif isinstance(column.type, Float):
              node.value.append((ScalarNode(tag='tag:yaml.org,2002:str', value=column.name), 
                                 dumper.represent_scalar(tag='tag:yaml.org,2002:float', value=str(getattr(obj, column.name)), style='')))
            elif isinstance(column.type, Boolean):
              node.value.append((ScalarNode(tag='tag:yaml.org,2002:str', value=column.name), 
                                 dumper.represent_scalar(tag='tag:yaml.org,2002:bool', value=str(getattr(obj, column.name)), style='')))
            else:
              raise TypeError("No scalar representation is implemented for SQLAlchemy column type {col_type}".format(column.type))
    return node

  def get_id(self,obj):
    # Return the sqlite id of the item so lists can be sorted by id
    return obj.id
  
  def get_dict_id(self,obj):
    # Return the sqlite id of the item so lists can be sorted by id
    return obj['id']