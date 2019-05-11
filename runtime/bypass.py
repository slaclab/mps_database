from sqlalchemy import Column, Integer, String, ForeignKey, Float, DateTime, func
from sqlalchemy.orm import relationship, backref
from runtime import RuntimeBase
import time

class Bypass(RuntimeBase):
  """
  Bypass class (bypasses table)

  Properties:
    startdate: when the bypass started
    duration: bypass time in seconds since startdate
    value: threshold value (either high or low)
    device_integrator: index of the bypassed integrator (for analog devices)

  References:
    device_id: points to the device that owns this threshold
  """
  __tablename__ = 'bypasses'
  id = Column(Integer, primary_key=True)
  startdate = Column(Integer) #time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(time.time())))
  duration = Column(Integer)
  value = Column(Integer)

#  device_id = Column(Integer)
  device_integrator = Column(Integer, default=0)
#  device = relationship("Device", uselist=False, back_populates="bypass0")
  device_id = Column(Integer, ForeignKey('devices.id'))

#  device_input_id = Column(Integer)
  device_input = relationship("DeviceInput", uselist=False, back_populates="bypass")
  device_input_id = Column(Integer, ForeignKey('device_inputs.id'))
