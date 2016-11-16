from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, backref
from models import Base

class DeviceType(Base):
  """
  DeviceType class (device_types table)

  Describe a class of devices, e.g. insertion device.

  Properties:
    name: meaningful and descriptive device type name

  Relationships:
    states: referanced by DeviceState, tells in which states this
            DeviceType can be (e.g. In/Out/Moving/Broken)
    devices: list of DigitalDevices that are of this DeviceType
  """
  __tablename__ = 'device_types'
  id = Column(Integer, primary_key=True)
  name = Column(String, nullable=False, unique=True)
  states = relationship("DeviceState", backref='device_type')
  devices = relationship("Device", backref='device_type')
