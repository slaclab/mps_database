from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, backref
from mps_database.models import Base

class DeviceType(Base):
  """
  DeviceType class (device_types table)

  Describe a class of devices, e.g. insertion device.

  Properties:
    name: base name for the PVs associated to this device
    description: 
    num_integrators: number of integrators for the device. This is applicable
                     to analog devices only, e.g. BPMs have 3 (X, Y and TMIT),
                     while other types may have from 1 up to 4.

  Relationships:
    states: referanced by DeviceState, tells in which states this
            DeviceType can be (e.g. In/Out/Moving/Broken)
    devices: list of DigitalDevices that are of this DeviceType
  """
  __tablename__ = 'device_types'
  id = Column(Integer, primary_key=True)
  name = Column(String, nullable=False)
  description = Column(String, nullable=False)
  num_integrators = Column(Integer, nullable=False, default=0)
  states = relationship("DeviceState", backref='device_type')
  devices = relationship("Device", backref='device_type', foreign_keys='Device.device_type_id')

