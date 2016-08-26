from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship, backref
from models import Base

class Device(Base):
  """
  Device class (devices table)

  This is a generic class that contains properties common to DigitalDevices
  and AnalogDevices.

  Properties:
    name: unique device name (possibly MAD device name)
    description: some extra information about this device
    z_position: linac Z position in ft

  References:
    application_id: application that owns this device

  """
  __tablename__ = 'devices'
  id = Column(Integer, primary_key=True)
  discriminator = Column('type', String(50))
  name = Column(String, unique=True, nullable=False)
  description = Column(String, nullable=True)
  z_position = Column(Float, nullable=True)
  application_id = Column(Integer, ForeignKey('applications.id'), nullable=False)
  __mapper_args__ = {'polymorphic_on': discriminator}

class DigitalDevice(Device):  
  """
  DigitalDevice class (digital_devices table)

  Relationships:
   inputs: list of DeviceInput that use this DigitalDevice
   fault_outputs: list of FaultInputs that use this DigitalDevice as input
  """
  __tablename__ = 'digital_devices'
  __mapper_args__ = {'polymorphic_identity': 'digital_device'}
  id = Column(Integer, ForeignKey('devices.id'), primary_key=True)
  device_type_id = Column(Integer, ForeignKey('device_types.id'), nullable=False)
  inputs = relationship("DeviceInput", backref='digital_device')
  fault_outputs = relationship("FaultInput", backref='device')

class AnalogDevice(Device):
  """
  AnalogDevice class (analog_devices table)

  References:
    channel_id: reference to the AnalogChannel that is connected to
                to the actual device

  Relationships:
    threshold_faults: list of ThresholdFaults that reference
                      this AnalogDevice
  """
  __tablename__ = 'analog_devices'
  __mapper_args__ = {'polymorphic_identity': 'analog_device'}
  id = Column(Integer, ForeignKey('devices.id'), primary_key=True)
  analog_device_type_id = Column(Integer, ForeignKey('analog_device_types.id'), nullable=False)
  channel_id = Column(Integer, ForeignKey('analog_channels.id'), nullable=False, unique=True)
  threshold_faults = relationship("ThresholdFault", backref='analog_device')
