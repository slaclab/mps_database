from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, backref
from models import Base

class FaultInput(Base):
  """
  FaultInput class (fault_inputs table)

  A DigitalFault (or only Fault) is composed of one or more FaultInputs.
  Each input represents one bit, the position of each bit is specified
  in each FaultInput. The DigitalDevice current value is composed by
  one or more FaultInputs.

  Properties:
    bit_position: the position for the DigitalDevice input bit

  References:
    fault_id: pointer to the Fault that uses this FaultInput
    device_id: pointer to the DigitalDevice providing this input
  """
  __tablename__ = 'fault_inputs'
  id = Column(Integer, primary_key=True)
  fault_id = Column(Integer, ForeignKey('faults.id'), nullable=False)
  bit_position = Column(Integer, nullable=False)
  device_id = Column(Integer, ForeignKey('digital_devices.id'), nullable=False)
