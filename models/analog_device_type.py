from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, backref
from models import Base

class AnalogDeviceType(Base):
  __tablename__ = 'analog_device_types'
  id = Column(Integer, primary_key=True)
  name = Column(String, nullable=False, unique=True)
  threshold_value_map_id = Column(Integer, ForeignKey('threshold_value_maps.id'), nullable=False)
  units = Column(String, nullable=False)
  analog_devices = relationship("AnalogDevice", backref='analog_device_type')