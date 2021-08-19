import datetime

from sqlalchemy import Column, Integer, String, DateTime
from mps_database.models import Base

class FaultHistory(Base):
  """
  FaultHistory class (fault_history table)

  Properties:
   timestamp: the timestamp of the fault event. Format is as follows
     in order to work with sqlite date/time functions: "YYYY-MM-DD HH:MM:SS.SSS"
   new_state: the state that was transitioned to in this fault event
                 
  """
  __tablename__ = 'fault_history'
  id = Column(Integer, primary_key=True)
  timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
  fault_id = Column(Integer, nullable=False)
  # new/old states should be active/inactive
  new_state = Column(String, nullable=False)
  old_state = Column(String, nullable=False)
  # Device state is the optional auxillary data
  device_state = Column(String, nullable=True)
