from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, backref
from models import Base

class DigitalChannel(Base):
  """
  DigitalChannnel class (digital_channels table)
  
  Properties:
   number: position of this channel in the card - starts at 0. The
           ApplicationCard checks if there are duplicate numbers and
           if the number does not exceed the maximum number of channels
   name: string identification for channel, this is used to compose PVs
         (e.g. PROF:GUNB:855:IN_LMTSW, where IN_LMTSW is the channel name)
   z_name: named state when value is zero (e.g. OUT or OFF) 
   o_name: named state when value is one (e.g. IN or ON)
   debounce: configurable channel debounce time
   alarm_state: define whether zero or one value is the fault state

  References:
   card_id: specifies the card that contains this channel

  Relationships:
   device_input: a DigitalChannel can be referenced by one or more
                 DeviceInputs (used by DigitalDevices)
  """
  __tablename__ = 'digital_channels'
  id = Column(Integer, primary_key=True)
  number = Column(Integer, nullable=False) #NOTE: Channel numbers need to start at 0, not 1.
  name = Column(String, nullable=False)
  z_name = Column(String, nullable=False)
  o_name = Column(String, nullable=False)
  alarm_state = Column(Integer, nullable=False, default=0)
  debounce = Column(Integer, nullable=False, default=10)
  card_id = Column(Integer, ForeignKey('application_cards.id'), nullable=False)
  device_input = relationship("DeviceInput", uselist=False, backref="channel")
  
class AnalogChannel(Base):
  """
  AnalogChannel class (analog_channels table)

  Properties:
   number: position of this channel in the card - starts at 0. The
           ApplicationCard checks if there are duplicate numbers and
           if the number does not exceed the maximum number of channels
   name: string identification for channel, this is used to compose PVs
         (e.g. PROF:GUNB:855:IN_LMTSW, where IN_LMTSW is the channel name)

  References:
   card_id: specifies the card that contains this channel

  Relationships:
   analog_device: the AnalogDevice that uses this channel
  """
  __tablename__ = 'analog_channels'
  id = Column(Integer, primary_key=True)
  number = Column(Integer, nullable=False)
  name = Column(String, unique=True, nullable=False)
  card_id = Column(Integer, ForeignKey('application_cards.id'), nullable=False)
  analog_device = relationship("AnalogDevice", uselist=False, backref="channel")
