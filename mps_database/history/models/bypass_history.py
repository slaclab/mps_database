import datetime

from sqlalchemy import Column, Integer, String, DateTime
from mps_database.models import Base

class BypassHistory(Base):
  """
  BypassHistory class (bypass_history table)

  Properties:
   timestamp: the timestamp of the fault event. Format is as follows
     in order to work with sqlite date/time functions: "YYYY-MM-DD HH:MM:SS.SSS"
   new_state: the state that was transitioned to in this fault event
   integrator: auxillary data found in previous EicHistory server
                 
  """
  __tablename__ = 'bypass_history'
  id = Column(Integer, primary_key=True)
  timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
  bypass_id = Column(Integer, nullable=False)
  new_state = Column(Integer, nullable=False)
  old_state = Column(Integer, nullable=False)
  integrator = Column(Integer, nullable=True)
