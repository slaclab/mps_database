from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, backref
from models import Base

class DeviceType(Base):
  __tablename__ = 'device_types'
  id = Column(Integer, primary_key=True)
  name = Column(String, nullable=False, unique=True)
  states = relationship("DeviceState", backref='device_type')
  devices = relationship("Device", backref='device_type')