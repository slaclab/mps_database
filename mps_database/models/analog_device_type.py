from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, backref
from mps_database.models import Base

class AnalogDeviceType(Base):
  """
  AnalogDeviceType class (analog_device_types table)

  Describe a class of analog devices, e.g. BPM Position or BPM TMIT.

  Properties:
    name: meaningful and descriptive device type name
    units: measurement unit (e.g. mm, pC, counts)

  Relationships:
    analog_devices: list of AnalogDevices that are of this AnalogDeviceType
  """
  __tablename__ = 'analog_device_types'
  id = Column(Integer, primary_key=True)
  name = Column(String, nullable=False, unique=True)
  threshold_value_map_id = Column(Integer, ForeignKey('threshold_value_maps.id'), nullable=False)
  units = Column(String, nullable=False)
  analog_devices = relationship("AnalogDevice", backref='analog_device_type')
