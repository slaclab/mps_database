from sqlalchemy import Column, Integer, String, DateTime
from mps_database.models import Base

import datetime

class InputHistory(Base):
  """
  InputHistory class (input_history table)

  Properties:
   timestamp: the timestamp of the fault event. Format is as follows
     in order to work with sqlite date/time functions: "YYYY-MM-DD HH:MM:SS.SSS"
   new_state: the state that was transitioned to in this fault event
                 
  """
  __tablename__ = 'input_history'
  id = Column(Integer, primary_key=True)
  timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
  #Old and new satates are based off of named values
  new_state = Column(String, nullable=False)
  old_state = Column(String, nullable=False)
  channel = Column(String, nullable=False) #DigitalChannel
  device = Column(String, nullable=False) #DigitalDevice 

