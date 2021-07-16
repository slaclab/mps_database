from sqlalchemy import Column, Integer, String, ForeignKey, Float, DateTime, func
from sqlalchemy.orm import relationship, backref
from mps_database.runtime import RuntimeBase
import time

class BypassHistory(RuntimeBase):
  """
  Bypass History class (history of bypasses table)

  Properties:
    value: threshold value (either high or low)

  References:
    device_id: points to the analog device that owns this bypass entry
  """
  __tablename__ = 'bypass_history'
  id = Column(Integer, primary_key=True)
  startdate = Column(Integer) 
  duration = Column(Integer)
  value = Column(Integer)

  user = Column(String, nullable=False)
  date = Column(DateTime(timezone=True), server_default=func.now())
  reason = Column(String, nullable=False)
  device_id = Column(Integer) # analog device id
  device_input_id = Column(Integer) # device_input id
