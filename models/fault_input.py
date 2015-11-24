from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, backref
from models import Base

class FaultInput(Base):
  __tablename__ = 'fault_inputs'
  id = Column(Integer, primary_key=True)
  fault_id = Column(Integer, ForeignKey('faults.id'), nullable=False)
  bit_position = Column(Integer, nullable=False)
  device_id = Column(Integer, ForeignKey('digital_devices.id'), nullable=False)