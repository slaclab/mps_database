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
                  models.FaultState,
                  models.AnalogDevice,
                  models.MitigationDevice,
                  models.BeamClass,
                  models.AllowedClass,
                   models.Condition,
                   models.IgnoreCondition,
                   models.ConditionInput]
  for model_class in model_classes:
    collection = session.query(model_class).order_by(model_class.id).all()
    
    yaml.dump({model_class.__name__: collection}, f, explicit_start=True)  
  f.close()

#This is a pyyaml representer for any object that inherits from SQLAlchemy's declarative base class.  
def model_representer(dumper, obj):
  node = MappingNode(tag=u'tag:yaml.org,2002:map', value=[], flow_style=False)
  for column in obj.__table__.columns:
    if isinstance(column.type, String):
      node.value.append((ScalarNode(tag=u'tag:yaml.org,2002:str', value=column.name), dumper.represent_scalar(tag=u'tag:yaml.org,2002:str', value=unicode(getattr(obj, column.name)), style='"')))
    elif isinstance(column.type, Integer):
      node.value.append((ScalarNode(tag=u'tag:yaml.org,2002:str', value=column.name), dumper.represent_scalar(tag=u'tag:yaml.org,2002:int', value=unicode(getattr(obj, column.name)), style='')))
    elif isinstance(column.type, Float):
      node.value.append((ScalarNode(tag=u'tag:yaml.org,2002:str', value=column.name), dumper.represent_scalar(tag=u'tag:yaml.org,2002:float', value=unicode(getattr(obj, column.name)), style='')))
    elif isinstance(column.type, Boolean):
      node.value.append((ScalarNode(tag=u'tag:yaml.org,2002:str', value=column.name), dumper.represent_scalar(tag=u'tag:yaml.org,2002:bool', value=unicode(getattr(obj, column.name)), style='')))
    else:
      raise TypeError("No scalar representation is implemented for SQLAlchemy column type {col_type}".format(column.type))

  # This code is to print out the attributes inherited from the class Device by the AnalogDevice and DigitalDevice
  if (hasattr(obj.__class__.__bases__[0],'__tablename__')):
    if (obj.__class__.__bases__[0].__tablename__ == "devices"):
      for column in obj.__class__.__bases__[0].__table__.columns:
        if (column.name != "type"):
          if isinstance(column.type, String):
            node.value.append((ScalarNode(tag=u'tag:yaml.org,2002:str', value=column.name), dumper.represent_scalar(tag=u'tag:yaml.org,2002:str', value=unicode(getattr(obj, column.name)), style='"')))
          elif isinstance(column.type, Integer):
            node.value.append((ScalarNode(tag=u'tag:yaml.org,2002:str', value=column.name), dumper.represent_scalar(tag=u'tag:yaml.org,2002:int', value=unicode(getattr(obj, column.name)), style='')))
          elif isinstance(column.type, Float):
            node.value.append((ScalarNode(tag=u'tag:yaml.org,2002:str', value=column.name), dumper.represent_scalar(tag=u'tag:yaml.org,2002:float', value=unicode(getattr(obj, column.name)), style='')))
          elif isinstance(column.type, Boolean):
            node.value.append((ScalarNode(tag=u'tag:yaml.org,2002:str', value=column.name), dumper.represent_scalar(tag=u'tag:yaml.org,2002:bool', value=unicode(getattr(obj, column.name)), style='')))
          else:
            raise TypeError("No scalar representation is implemented for SQLAlchemy column type {col_type}".format(column.type))
 
  return node
