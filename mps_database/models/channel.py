from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, backref
from mps_database.models import Base

class DigitalOutChannel(Base):
  """
  DigitalOutChannnel class (digital_out_channels table)
  
  Properties:
   number: position of this channel in the card - starts at 0. The
           ApplicationCard checks if there are duplicate numbers and
           if the number does not exceed the maximum number of channels
   name: string identification for channel, this is used to compose PVs
         (e.g. PROF:GUNB:855:IN_LMTSW, where IN_LMTSW is the channel name)
  References:
   card_id: specifies the card that contains this channel
  """
  __tablename__ = 'digital_out_channels'
  id = Column(Integer, primary_key=True)
  number = Column(Integer, nullable=False) #NOTE: Channel numbers need to start at 0, not 1.
  name = Column(String, nullable=False)
  card_id = Column(Integer, ForeignKey('application_cards.id'), nullable=False)
  mitigation_devices = relationship("MitigationDevice", backref='digital_out_channel')

class DigitalChannel(Base):
  """
  DigitalChannnel class (digital_channels table)
  
  Properties:
   number: position of this channel in the card - starts at 0. The
           ApplicationCard checks if there are duplicate numbers and
           if the number does not exceed the maximum number of channels.
           Channels number 32 to 47 are reserved for virtual inputs - i.e.
           inputs settable by software
   name: string identification for channel, this is used to compose PVs
         (e.g. PROF:GUNB:855:IN_LMTSW, where IN_LMTSW is the channel name)
   z_name: named state when value is zero (e.g. OUT or OFF) 
   o_name: named state when value is one (e.g. IN or ON)
   num_inputs: number of monitored PVs (default=0). If the digital channel is 
               the result of calculations based on soft inputs (CA) then
               this has the number of PVs listed in 'monitored_pvs'
   monitored_pvs: string containing one or more PV names that should be
                  used by the link node to calculate the value of the soft channel.
                  The number of PVs listed on this string is given by the num_inputs.
                  PVs must be separated by commas. (default="")
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
  description = Column(String,nullable=False,default="")
  num_inputs = Column(Integer, nullable=False, default=0) # for SoftChannels only
  monitored_pvs = Column(String, nullable=False, default="") # for SoftChannels only
  alarm_state = Column(Integer, nullable=False, default=0)
  debounce = Column(Integer, nullable=False, default=10)
  card_id = Column(Integer, ForeignKey('application_cards.id'), nullable=False)
  device_input = relationship("DeviceInput", backref="channel")

  def is_virtual(self):
    if (self.number >= 32):
      return True
    else:
      return False
  
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
  name = Column(String, nullable=False)
  card_id = Column(Integer, ForeignKey('application_cards.id'), nullable=False)
  analog_device = relationship("AnalogDevice", uselist=False, backref="channel")

  def get_bay(self):
    if self.number > 2:
      return 1
    else:
      return 0
