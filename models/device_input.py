from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, backref
from models import Base

class DeviceInput(Base):
  """
  DeviceInput class (device_input table)

  Properties:
   bit_position: specifies which bit this input should be used when
                 calculating the DigitalDevice value/state
   fault_value: defines which value (one or zero) means that the device
                is faulted. When a new value is received and is the same
                as fault_value it gets latched.
                 
  References:
    digital_device_id: the DigitalDevice that uses this DeviceInput
    channel_id: the DigitalChannel connected to this DeviceInput
  """
  __tablename__ = 'device_inputs'
  id = Column(Integer, primary_key=True)
  digital_device_id = Column(Integer, ForeignKey('digital_devices.id'), nullable=False)
  bit_position = Column(Integer, nullable=False)
  fault_value = Column(Integer, nullable=False)
  channel_id = Column(Integer, ForeignKey('digital_channels.id'), nullable=False, unique=True)
