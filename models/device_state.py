from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, backref
from models import Base

class DeviceState(Base):
  __tablename__ = 'device_states'
  id = Column(Integer, primary_key=True)
  name = Column(String, nullable=False)
  value = Column(Integer, nullable=False)
  device_id = Column(Integer, ForeignKey('devices.id'), nullable=False)