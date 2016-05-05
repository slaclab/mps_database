from mps_config import MPSConfig
import models
import yaml
from yaml import MappingNode, ScalarNode
from sqlalchemy import Column, Integer, Float, String, Boolean
def dump_db_to_yaml(mps_config, filename):
  session = mps_config.session
  f = file(filename, 'w')
  yaml.add_multi_representer(models.Base, model_representer)
  model_classes = [models.Crate,
                  models.ApplicationType,
                  models.ApplicationCard,
                  models.DigitalChannel,
                  models.AnalogChannel,
                  models.DeviceType,
                  models.DeviceState,
                  models.DigitalDevice,
                  models.DeviceInput,
                  models.Fault,
                  models.FaultInput,
                  models.DigitalFaultState,
                  models.ThresholdValueMap,
                  models.ThresholdValue,
                  models.AnalogDeviceType,
                  models.AnalogDevice,
                  models.ThresholdFault,
                  models.ThresholdFaultState,
                  models.MitigationDevice,
                  models.BeamClass,
                  models.AllowedClass]
  for model_class in model_classes:
    collection = session.query(model_class).order_by(model_class.id).all()
    
    yaml.dump({model_class.__name__: collection}, f, explicit_start=True)  
  f.close()
  
def model_representer(dumper, obj):
  node = MappingNode(tag=u'tag:yaml.org,2002:map', value=[], flow_style=False)
  for column in obj.__table__.columns:
    if getattr(obj, column.name) == None:
      continue
    print("Generating node for col_name = {col_name}, type = {col_type}, val = {val}".format(col_name=column.name, col_type=column.type, val=str(getattr(obj, column.name))))
    if isinstance(column.type, String):
      node.value.append((ScalarNode(tag=u'tag:yaml.org,2002:str', value=column.name), (ScalarNode(tag=u'tag:yaml.org,2002:str', value=getattr(obj, column.name), style='"'))))
    elif isinstance(column.type, Integer):
      node.value.append((ScalarNode(tag=u'tag:yaml.org,2002:str', value=column.name), (ScalarNode(tag=u'tag:yaml.org,2002:int', value=str(getattr(obj, column.name)), style=''))))
    elif isinstance(column.type, Float):
      node.value.append((ScalarNode(tag=u'tag:yaml.org,2002:str', value=column.name), (ScalarNode(tag=u'tag:yaml.org,2002:float', value=str(getattr(obj, column.name)), style=''))))
    elif isinstance(column.type, Boolean):
      node.value.append((ScalarNode(tag=u'tag:yaml.org,2002:str', value=column.name), (ScalarNode(tag=u'tag:yaml.org,2002:bool', value=str(getattr(obj, column.name)), style=''))))
  return node