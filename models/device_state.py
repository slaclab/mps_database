from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, backref
from models import Base

class DeviceState(Base):
  __tablename__ = 'device_states'
  id = Column(Integer, primary_key=True)
  name = Column(String, nullable=False)
  value = Column(Integer, nullable=False)
  device_type_id = Column(Integer, ForeignKey('device_types.id'), nullable=False)