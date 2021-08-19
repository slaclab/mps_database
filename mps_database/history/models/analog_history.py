import datetime

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship, backref
from mps_database.models import Base

class AnalogHistory(Base):
  """
  AnalogHistory class (analog_history table)

  Properties:
   timestamp: the timestamp of the fault event. Format is as follows
     in order to work with sqlite date/time functions: "YYYY-MM-DD HH:MM:SS.SSS"
   new_state: the state that was transitioned to in this fault event

  """
  __tablename__ = 'analog_history'
  id = Column(Integer, primary_key=True)
  timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
  channel = Column(Integer, nullable=False) # AnalogChannel from id(AnalogDevice)
  # States are converted to hex? 
  new_state = Column(Integer, nullable=False)
  old_state = Column(Integer, nullable=False)
