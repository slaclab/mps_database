import datetime

from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship, backref
from mps_database.models import Base

class FaultHistory(Base):
  """
  FaultHistory class (fault_history table)

  Properties:
   timestamp: the timestamp of the fault event. Format is as follows
     in order to work with sqlite date/time functions: "YYYY-MM-DD HH:MM:SS.SSS"
   new_state: the state that was transitioned to in this fault event
                 
  References:
    beam_class: The relevant beam class value - is this possible?
  """
  __tablename__ = 'fault_history'
  id = Column(Integer, primary_key=True)
  fault_id = Column(Integer, nullable=False)
  timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
