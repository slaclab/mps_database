from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.orm import relationship, backref
from models import Base

class Device(Base):
  __tablename__ = 'devices'
  id = Column(Integer, primary_key=True)
  name = Column(String, unique=True, nullable=False)
  description = Column(String, nullable=True)
  z_position = Column(Float, nullable=True)
  states = relationship("DeviceState", backref='device')
  inputs = relationship("DeviceInput", backref='device')
  fault_outputs = relationship("FaultInput", backref='device')