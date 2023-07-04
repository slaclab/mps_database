from sqlalchemy import Column, Integer, String, Float,Boolean, ForeignKey
from sqlalchemy.orm import relationship, backref
from mps_database.models import Base

class Channel(Base):
  """
  Channel class (channels table)

  Properties:
    number: The channel number
    name: PV name of this channel
    z_location: z location in ft along the linac (linac_z)
    auto_reset: defines whether the faulted device input value should be
            cleared once a good value is received. The auto-reset does
            not work if the input is used by a device with fast evaluation.
            Default value is False - i.e. a faulted input is held until
            it is reset by operators.
    evaluation: define if device state is evaluated by fast(1) or slow(0) logic.
            default value is slow(0)

  References:
    card_id: specifies the card that contains this channel

  The discriminator field is used to define whether the device is digital (digital_channel)
  or analog (analog_channel)
  """
  __tablename__ = 'channels'
  id = Column(Integer, primary_key=True)
  discriminator = Column('type',String(50))
  number = Column(Integer,nullable=False)
  name = Column(String, nullable=False)
  z_location = Column(Integer,nullable=False)
  auto_reset = Column(Integer, nullable=False, default=0)
  evaluation = Column(Integer, nullable=False, default=0)
  card_id = Column(Integer,ForeignKey('application_cards.id'),nullable=False)
  card = relationship("ApplicationCard",back_populates='channels')
  fault_input = relationship("FaultInput",back_populates='channel')
  __mapper_args__ = {'polymorphic_on': discriminator}



class DigitalChannel(Channel):
  """
  DigitalChannnel class (digital_channels table)
  
  Properties:
   z_name: named state when value is zero (e.g. OUT or OFF) 
   o_name: named state when value is one (e.g. IN or ON)
   monitored_pv:  string containing one PV name that should be
                  used by the link node to calculate the value of the soft channel.
   debounce: configurable channel debounce time
   alarm_state: define whether zero or one value is the fault state


  References:
   card_id: specifies the card that contains this channel

  Relationships:
   device_input: a DigitalChannel can be referenced by one or more
                 DeviceInputs (used by DigitalDevices)
  """
  __tablename__ = 'digital_channels'
  __mapper_args__ = {'polymorphic_identity': 'digital_channel'}
  id = Column(Integer,ForeignKey('channels.id'), primary_key=True)
  z_name = Column(String, nullable=False)
  o_name = Column(String, nullable=False)
  monitored_pv = Column(String, nullable=False, default="") # for SoftChannels only
  debounce = Column(Integer, nullable=False, default=10)
  alarm_state = Column(Integer,nullable=False,default=0)
  ignore_condition = relationship("IgnoreCondition", back_populates='digital_channel')

  
class AnalogChannel(Channel):
  """
  AnalogChannel class (analog_channels table)

  Properties:
    offset: The unit conversion offset in raw
    slope: The unit conversion slope in egu/raw
    egu: The engineering units to display
    gain_bay: the gain control chassis bay
    gain_channel: the gain control chassis channel
    integrator: integrator this input corresponds to:
                BPM: TMIT, X, Y

  References:
   card_id: specifies the card that contains this channel

  Relationships:
   analog_device: the AnalogDevice that uses this channel
  """
  __tablename__ = 'analog_channels'
  __mapper_args__ = {'polymorphic_identity': 'analog_channel'}
  id = Column(Integer,ForeignKey('channels.id'), primary_key=True)
  offset = Column(Float,nullable=True)
  slope = Column(Float,nullable=True)
  integrator = Column(Integer, nullable=False,default=0)
  gain_bay = Column(Integer, nullable=True)
  gain_channel = Column(Integer,nullable=True)
