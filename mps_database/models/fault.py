from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.orm import relationship, backref
from sqlalchemy.orm import object_session
from mps_database.models import Base
from .fault_input import FaultInput
from .fault_state import FaultState
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
    states: list of FaultStates that belong to this fault
    inputs: list of FaultInputs for this fault
  """
  __tablename__ = 'faults'
  id = Column(Integer, primary_key=True)
  name = Column(String, nullable=False)
  description = Column(String, nullable=True)
  states = relationship("FaultState", backref='fault')
  inputs = relationship("FaultInput", backref='fault')
  
  def fault_value(self, device_states):
    fault_value = 0
    for fault_input in self.inputs:
      bit_length = len(fault_input.device.inputs)
      input_value = device_states[fault_input.device_id]
      fault_value = fault_value | (input_value << (bit_length*fault_input.bit_position))
    return fault_value

  def get_integrator_index(self):
    session = object_session(self)
    fault_states = session.query(FaultState).filter(FaultState.fault_id==self.id).all()
    for state in fault_states:
      bit_index=0
      bitFound=False
      while not bitFound:
        b=(state.device_state.mask>>bit_index) & 1
        if b==1:
          bitFound=True
        else:
          bit_index=bit_index+1
          if bit_index==32:
            done=True
            bit_index=-1
        if bit_index==-1:
          print "ERROR: invalid threshold mask (" + hex(state.device_state.mask)
          return None

        # Convert bit_index to integrator index
        # BPM: bit 0-7 -> X, bit 8-15 -> Y, bit 16-23 -> CHRG
        # Non-BPM: bit 0-7 -> INT0, bit 8-15 -> INT1, bit 16-23 -> INT2, bit 24-31 -> INT3
        int_index=0
        if (bit_index >= 8 and bit_index <= 15):
          int_index = 1
        elif (bit_index >= 16 and bit_index <= 23):
          int_index = 2
        elif (bit_index >= 24 and bit_index <= 31):
          int_index = 3

      return int_index
