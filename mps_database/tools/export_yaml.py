#!/usr/bin/env python
from mps_database.mps_config import MPSConfig, models, runtime
from sqlalchemy import MetaData
from mps_database.tools.mps_names import MpsName
from mps_database.tools.mps_reader import MpsReader, MpsDbReader
from sqlalchemy import Column, Integer, Float, String, Boolean
import subprocess
from latex import Latex
import math
import argparse
import time
import yaml
from yaml import MappingNode, ScalarNode
import os
import sys

class ExportYaml(MpsReader):

  def __init__(self, db_file, template_path, dest_path,clean,verbose):
    MpsReader.__init__(self,db_file=db_file,dest_path=dest_path,template_path=template_path,clean=clean,verbose=verbose)
    self.verbose = verbose

  def export(self,mps_db_session):
    if self.verbose:
      print("INFO: Starting Export Yaml...")
    for cn in range(0,3):
      yaml_filename = yaml_filename = '{0}/mps_config-cn{1}-{2}.yaml'.format(self.dest_path,cn+1,self.config_version)
      self.dump_yaml(mps_db_session,yaml_filename,cn)
      cmd = "whoami"
      process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
      user_name, error = process.communicate()
      cmd = "md5sum {0}".format(self.database)
      process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
      md5sum_output, error = process.communicate()

      md5sum_tokens = md5sum_output.split()
      file1 = open(yaml_filename,"a")
      file1.write("---\n")
      file1.write("DatabaseInfo:\n")
      file1.write("- source: {0}\n".format(self.database))
      file1.write("  date: {0}\n".format(time.asctime(time.localtime(time.time()))))
      file1.write("  user: {0}\n".format(user_name.strip()))
      file1.write("  md5sum: {0}\n".format(md5sum_tokens[0].strip()))
      file1.close()     
    if self.verbose:
      print('........Done Exporting Yaml')  

  def dump_yaml(self,session,filename,cn):
    f = open(filename,"w")
    self.dump_general_to_yaml(session,f)
    if cn == 0:
      self.dump_link_nodes_to_yaml(session,f,self.cn1)
    elif cn == 1:
      self.dump_link_nodes_to_yaml(session,f,self.cn2)
    elif cn == 2:
      self.dump_link_nodes_to_yaml(session,f,self.cn3)

  def dump_general_to_yaml(self,session,f):
    yaml.add_multi_representer(models.Base, self.model_representer)
    model_classes = [models.ApplicationType,
                     models.DeviceType, 
                     models.DeviceState, 
                     models.MitigationDevice,
                     models.BeamDestination,
                     models.BeamClass]
    for model_class in model_classes:
      collection = session.query(model_class).order_by(model_class.id).all()
      yaml.dump({model_class.__name__: collection}, f, explicit_start=True)

  def dump_link_nodes_to_yaml(self,session,f,groups):
    yaml.add_multi_representer(models.Base, self.model_representer)
    #Link Nodes:
    link_nodes = session.query(models.LinkNode).filter(models.LinkNode.group.in_(groups)).order_by(models.LinkNode.id).all()
    yaml.dump({models.LinkNode.__name__: link_nodes}, f, explicit_start=True) 
    #Crates
    crateIDs = []
    link_node_ids = []
    for link_node in link_nodes:
      crateIDs.append(link_node.crate_id)
      link_node_ids.append(link_node.id)
    crates = session.query(models.Crate).filter(models.Crate.id.in_(crateIDs)).order_by(models.Crate.id).all()
    yaml.dump({models.Crate.__name__: crates}, f, explicit_start=True)
    #Application Cards
    app_cards = session.query(models.ApplicationCard).filter(models.ApplicationCard.link_node_id.in_(link_node_ids)).order_by(models.ApplicationCard.id).all()
    yaml.dump({models.ApplicationCard.__name__: app_cards}, f, explicit_start=True)
    app_ids = []  
    for app in app_cards:
      app_ids.append(app.id)
    #DigitalChannels
    digital_channels = session.query(models.DigitalChannel).filter(models.DigitalChannel.card_id.in_(app_ids)).order_by(models.DigitalChannel.id).all()
    yaml.dump({models.DigitalChannel.__name__: digital_channels}, f, explicit_start=True)
    digital_channel_ids = []
    for digital_channel in digital_channels:
      digital_channel_ids.append(digital_channel.id)
    #Analog Channels
    analog_channels = session.query(models.AnalogChannel).filter(models.AnalogChannel.card_id.in_(app_ids)).order_by(models.AnalogChannel.id).all()
    yaml.dump({models.AnalogChannel.__name__: analog_channels}, f, explicit_start=True)

    #DigitalDevice
    digital_device = session.query(models.DigitalDevice).filter(models.DigitalDevice.card_id.in_(app_ids)).order_by(models.DigitalDevice.id).all()
    yaml.dump({models.DigitalDevice.__name__: digital_device}, f, explicit_start=True)
    device_ids = []
    for dig in digital_device:
      device_ids.append(dig.id)

    #AnalogDevice
    analog_device = session.query(models.AnalogDevice).filter(models.AnalogDevice.card_id.in_(app_ids)).order_by(models.AnalogDevice.id).all()
    yaml.dump({models.AnalogDevice.__name__: analog_device}, f, explicit_start=True)
    for ana in analog_device:
      device_ids.append(ana.id)

    # Ignore Conditions
    ignore_conditions = session.query(models.IgnoreCondition).filter(models.IgnoreCondition.device_id.in_(device_ids)).all()
    yaml.dump({models.IgnoreCondition.__name__:ignore_conditions}, f, explicit_start=True)

    #DeviceInput
    device_inputs = []
    for digital_channel_id in digital_channel_ids:
      device_input = session.query(models.DeviceInput).filter(models.DeviceInput.channel_id == digital_channel_id).order_by(models.DeviceInput.id).all()
      device_inputs.extend(device_input)
    yaml.dump({models.DeviceInput.__name__: device_inputs}, f, explicit_start=True)

    #FaultInput
    fault_inputs = []
    for device_id in device_ids:
      fault_input = session.query(models.FaultInput).filter(models.FaultInput.device_id == device_id).order_by(models.FaultInput.id).all()
      fault_inputs.extend(fault_input)
    yaml.dump({models.FaultInput.__name__: fault_inputs}, f, explicit_start=True)  
    fault_ids = []
    for fi in fault_inputs:
      if fi.fault_id not in fault_ids:
        fault_ids.append(fi.fault_id)
    #return fault_ids

    #Fault
    faults = []
    for fid in fault_ids:
      fault = session.query(models.Fault).filter(models.Fault.id == fid).order_by(models.Fault.id).all()
      faults.extend(fault)
    yaml.dump({models.Fault.__name__: faults}, f, explicit_start=True) 


    #FaultState
    fault_states = []
    for fid in fault_ids:
      fault_state = session.query(models.FaultState).filter(models.FaultState.fault_id == fid).order_by(models.FaultState.id).all()
      fault_states.extend(fault_state)
    yaml.dump({models.FaultState.__name__: fault_states}, f, explicit_start=True)
    fs_ids = []
    for fs in fault_states:
      fs_ids.append(fs.id)

    # Condition Inputs
    c_inputs = []
    condition_inputs = session.query(models.ConditionInput).filter(models.ConditionInput.fault_state_id.in_(fs_ids)).all()
    yaml.dump({models.ConditionInput.__name__: condition_inputs}, f, explicit_start=True)
    for c in condition_inputs:
      c_inputs.append(c.condition_id)

    # Conditions
    conditions = session.query(models.Condition).filter(models.Condition.id.in_(c_inputs)).all()
    yaml.dump({models.Condition.__name__: conditions}, f, explicit_start=True)

    #AllowedClass
    #allowed_class = session.query(models.AllowedClass).filter(models.AllowedClass.fault_state_id.in_(fs_ids)).order_by(models.AllowedClass.id).all()
    #yaml.dump({models.AllowedClass.__name__: allowed_class}, f, explicit_start=True)
    #allowed_classes = []
    #for fs_id in fs_ids:
    #  allowed_class = session.query(models.AllowedClass).filter(models.AllowedClass.fault_state_id == fs_id).order_by(models.AllowedClass.id).all()
    #  allowed_classes.extend(allowed_class)
    allowed_class = session.query(models.AllowedClass).join(models.FaultState, models.AllowedClass.fault_state_id == models.FaultState.id).join(models.Fault, models.FaultState.fault_id == models.Fault.id).join(models.FaultInput, models.FaultInput.fault_id == models.Fault.id).join(models.Device, models.FaultInput.device_id == models.Device.id).join(models.ApplicationCard, models.Device.card_id == models.ApplicationCard.id).join(models.LinkNode, models.ApplicationCard.link_node_id == models.LinkNode.id).filter(models.LinkNode.group.in_(groups)).order_by(models.AllowedClass.id).all()
    yaml.dump({models.AllowedClass.__name__: allowed_class}, f, explicit_start=True)
    

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
      if (obj.__class__.__bases__[0].__tablename__ == "devices"):
        for column in obj.__class__.__bases__[0].__table__.columns:
          if (column.name != "type"):
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
