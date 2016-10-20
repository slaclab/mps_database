from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.orm import relationship, backref
from models import Base
from .fault_input import FaultInput
from .device import Device

class Condition(Base):
  """
  Condition class (conditions table)

  Describe a condition that is composed of current values of one or more 
  faults (digital and/or analog). Each fault input is represented by a bit
  (starting at zero). When the state of the input faults match the 
  condition value it becomes valid.

  A condition is used to ignore one ore more faults (digital and/or analog)

  Properties:
    name: condition identifier
    description: short description 
    value: bit mask used to verify if condition is met or not. 

  Relationships:
    ignore_conditions: list of fault states that compose this condition
    condition_inputs: list of fault states that are ignored when condition is true
  """
  __tablename__ = 'conditions'
  id = Column(Integer, primary_key=True)
  name = Column(String, unique=True, nullable=False)
  description = Column(String, nullable=True)
  value = Column(Integer, nullable=False)
  ignore_conditions = relationship("IgnoreCondition", backref='condition')
  condition_inputs = relationship("ConditionInput", backref='condition')
  
