from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.orm import relationship, backref
from models import Base
from .fault_input import FaultInput
from .device import Device

class Fault(Base):
  """
  Fault class (faults table)

  Describe a digital Fault, which is composed of one or more FaultInputs
  that make up the Fault value. 

  Properties:
    name: short fault identifier
    description: short explanation of the fault

  Relationships:
    states: list of DigitalFaultStates that belong to this fault
    inputs: list of FaultInputs for this fault
  """
  __tablename__ = 'faults'
  id = Column(Integer, primary_key=True)
  name = Column(String, unique=True, nullable=False)
  description = Column(String, nullable=True)
  states = relationship("DigitalFaultState", backref='fault')
  inputs = relationship("FaultInput", backref='fault')
  
  def fault_value(self, device_states):
    fault_value = 0
    for fault_input in self.inputs:
      bit_length = len(fault_input.device.inputs)
      input_value = device_states[fault_input.device_id]
      fault_value = fault_value | (input_value << (bit_length*fault_input.bit_position))
    return fault_value
