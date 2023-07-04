from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, backref
from mps_database.models import Base

class FaultInput(Base):
  """
  DigitalFaultInput class (device_input table)

  Properties:
    bit_position: specifies which bit this input should be used when
                 calculating the Fault value/state
    mask: For analog faults, the bitmask of that integrator/fault
                 
  References:
    channel_id: the DigitalChannel connected to this DigitalFaultInput
  """
  __tablename__ = 'fault_inputs'
  id = Column(Integer, primary_key=True)
  fault_id = Column(Integer, ForeignKey('faults.id'), nullable=False)
  fault = relationship("Fault",back_populates="fault_inputs")
  bit_position = Column(Integer, nullable=False,default=0)
  channel = relationship("Channel",back_populates='fault_input')
  channel_id = Column(Integer,ForeignKey('channels.id'),nullable=True)
