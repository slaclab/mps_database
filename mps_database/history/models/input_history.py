from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship, backref
from mps_database.models import Base

class InputHistory(Base):
  """
  InputHistory class (input_history table)

  Properties:
   timestamp: the timestamp of the fault event. Format is as follows
     in order to work with sqlite date/time functions: "YYYY-MM-DD HH:MM:SS.SSS"
   new_state: the state that was transitioned to in this fault event
                 
  References:
    beam_class: The relevant beam class value - is this possible?
  """
  __tablename__ = 'input_history'
  id = Column(Integer, primary_key=True)
  timestamp = Column(String, nullable=False)
  new_state = Column(Integer, nullable=False)
  previous_state = Column(Integer, nullable=False)
  #beam_class = Column(Integer, ForeignKey('beam_class.id'), nullable=False, unique=True)
