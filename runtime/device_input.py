from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, backref
from runtime import RuntimeBase

class DeviceInput(RuntimeBase):
  """
  DeviceInput class (device_input table)

  Properties:
    mpsdb_id: id from the MPS database for this device_input
                 
  References:
    device_id: the DigitalDevice that uses this DeviceInput
    channel_id: the DigitalChannel connected to this DeviceInput
  """
  __tablename__ = 'device_inputs'
  id = Column(Integer, primary_key=True)
  device_id = Column(Integer, ForeignKey('devices.id'), nullable=False)
  mpsdb_id = Column(Integer, nullable=False)
  pv_name = Column(String)

  #  bypass_id = Column(Integer, ForeignKey('bypasses.id'))
  bypass = relationship("Bypass", back_populates="device_input")
