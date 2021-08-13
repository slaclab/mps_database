import datetime

from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship, backref
from mps_database.models import Base

class FaultState(Base):
  """
  FaultState class (fault_state table)

  Properties:
   timestamp: the timestamp of the fault event. Format is as follows
     in order to work with sqlite date/time functions: "YYYY-MM-DD HH:MM:SS.SSS"
   new_state: the state that was transitioned to in this fault event
                 
  """
  __tablename__ = 'fault_state'
  id = Column(Integer, primary_key=True)
  fault_id = Column(Integer, nullable=False)
  timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
  new_state = Column(Integer, nullable=False)
  old_state = Column(Integer, nullable=False)
  device_state = Column(Integer, nullable=True)
