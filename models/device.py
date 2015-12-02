from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship, backref
from models import Base

class Device(Base):
  __tablename__ = 'devices'
  id = Column(Integer, primary_key=True)
  discriminator = Column('type', String(50))
  name = Column(String, unique=True, nullable=False)
  description = Column(String, nullable=True)
  z_position = Column(Float, nullable=True)
  __mapper_args__ = {'polymorphic_on': discriminator}

class DigitalDevice(Device):  
  __tablename__ = 'digital_devices'
  __mapper_args__ = {'polymorphic_identity': 'digital_device'}
  id = Column(Integer, ForeignKey('devices.id'), primary_key=True)
  device_type_id = Column(Integer, ForeignKey('device_types.id'), nullable=False)
  inputs = relationship("DeviceInput", backref='digital_device')
  fault_outputs = relationship("FaultInput", backref='device')

class AnalogDevice(Device):
  __tablename__ = 'analog_devices'
  __mapper_args__ = {'polymorphic_identity': 'analog_device'}
  id = Column(Integer, ForeignKey('devices.id'), primary_key=True)
  analog_device_type_id = Column(Integer, ForeignKey('analog_device_types.id'), nullable=False)
  channel_id = Column(Integer, ForeignKey('channels.id'), nullable=False, unique=True)
  threshold_faults = relationship("ThresholdFault", backref='analog_device')