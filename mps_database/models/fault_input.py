from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from mps_database.models import Base

class FaultInput(Base):
  """
  FaultInput class

  A fault input is a building block of a fault.  Each fault input links a channel
  to a fault.  It also contains the bit position so the final fault value can be calculated

  Properties:
    bit_position: specifies which bit this input should be used when
                 calculating the Fault value/state                 
  References:
    channel: the Channel connected to this FaultInput
    fault: the Fault connected to this FaultInput
  """
  __tablename__ = 'fault_inputs'
  id = Column(Integer, primary_key=True)
  fault_id = Column(Integer, ForeignKey('faults.id'), nullable=False)
  fault = relationship("Fault",back_populates="fault_inputs")
  bit_position = Column(Integer, nullable=False,default=0)
  channel = relationship("Channel",back_populates='fault_input')
  channel_id = Column(Integer,ForeignKey('channels.id'),nullable=True)
