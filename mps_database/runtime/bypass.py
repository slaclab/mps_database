from sqlalchemy import Column, Integer, String, ForeignKey, Float, DateTime, func
from sqlalchemy.orm import relationship, backref
from mps_database.runtime import RuntimeBase
import time

class Bypass(RuntimeBase):
  """
  Bypass class (bypasses table)

  Properties:
    startdate: when the bypass started
    duration: bypass time in seconds since startdate
    value: bypass value (either 1 or 0)
    device_integrator: index of the bypassed integrator (for analog devices)
    pv_name: base name for the bypass pvs (for both analog and digital)

  References:
    device_id: points to the device that owns this threshold
  """
  __tablename__ = 'bypasses'
  id = Column(Integer, primary_key=True)
  startdate = Column(Integer) #time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(time.time())))
  duration = Column(Integer)
  value = Column(Integer)
  pv_name = Column(String)

  device_integrator = Column(Integer, default=0)
  device_id = Column(Integer, ForeignKey('devices.id'))

  device_input = relationship("DeviceInput", uselist=False, back_populates="bypass")
  device_input_id = Column(Integer)
