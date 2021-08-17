import datetime

from sqlalchemy import Column, Integer, String, DateTime
from mps_database.models import Base

class MitigationType(Base):
  """
  MitigationType class (mitigation_type table)

  Properties:
   timestamp: the timestamp of the fault event. Format is as follows
     in order to work with sqlite date/time functions: "YYYY-MM-DD HH:MM:SS.SSS"
   new_state: the state that was transitioned to in this fault event
                 
  """
  __tablename__ = 'mitigation_type'
  id = Column(Integer, primary_key=True)
  timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
  # Device corresponds to BeamDestination
  device = Column(String, nullable=False)
  # Both correspond to BeamClass values, they just iterate
  new_state = Column(String, nullable=False)
  old_state = Column(String, nullable=False)
