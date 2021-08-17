from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship, backref
from mps_database.models import Base

class DeviceInput(Base):
  """
  DeviceInput class (device_input table)

  Properties:
   timestamp: the timestamp of the fault event. Format is as follows
     in order to work with sqlite date/time functions: "YYYY-MM-DD HH:MM:SS.SSS"
   new_state: the state that was transitioned to in this fault event
                 
  """
  __tablename__ = 'device_input'
  id = Column(Integer, primary_key=True)
  timestamp = Column(String, nullable=False)
  #Old and new satates are based off of named values
  new_state = Column(String, nullable=False)
  old_state = Column(String, nullable=False)
  channel = Column(String, nullable=False) #DigitalChannel
  device = Column(String, nullable=False) #DigitalDevice 

