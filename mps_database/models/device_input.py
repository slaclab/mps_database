from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship, backref
from mps_database.models import Base

class DeviceInput(Base):
  """
  DeviceInput class (device_input table)

  Properties:
   bit_position: specifies which bit this input should be used when
                 calculating the DigitalDevice value/state
   fault_value: defines which value (one or zero) means that the device
                is faulted. When a new value is received and is the same
                as fault_value it gets latched.
    auto_reset: defines whether the faulted device input value should be
                cleared once a good value is received. The auto-reset does
                not work if the input is used by a device with fast evaluation.
                Default value is False - i.e. a faulted input is held until
                it is reset by operators.
                 
  References:
    digital_device_id: the DigitalDevice that uses this DeviceInput
    channel_id: the DigitalChannel connected to this DeviceInput
  """
  __tablename__ = 'device_inputs'
  id = Column(Integer, primary_key=True)
  digital_device_id = Column(Integer, ForeignKey('digital_devices.id'), nullable=False)
  bit_position = Column(Integer, nullable=False)
  auto_reset = Column(Integer, nullable=False, default=0)
  fault_value = Column(Integer, nullable=False)
  channel_id = Column(Integer, ForeignKey('digital_channels.id'), nullable=False, unique=False)
