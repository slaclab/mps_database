from sqlalchemy import Column, Integer, String, Float,Boolean, ForeignKey
from sqlalchemy.orm import relationship, object_session
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
    card: specifies the card that contains this channel

  The discriminator field is used to define whether the device is digital (digital_channel)
  or analog (analog_channel)
  """
  __tablename__ = 'channels'
  id = Column(Integer, primary_key=True)
  discriminator = Column('type',String(50))
  number = Column(Integer,nullable=False)
  name = Column(String, nullable=False)
  z_location = Column(Float,nullable=False)
  auto_reset = Column(Integer, nullable=False, default=0)
  evaluation = Column(Integer, nullable=False, default=0)
  card_id = Column(Integer,ForeignKey('application_cards.id'),nullable=False)
  card = relationship("ApplicationCard",back_populates='channels')
  fault_input = relationship("FaultInput",back_populates='channel')
  __mapper_args__ = {'polymorphic_on': discriminator}

  def get_channel_properties(self):
    all_macros = []
    if self.discriminator == "digital_channel":
      all_macros.append(self._build_macros())
    else:
      states = self.get_fault_states()
      if states is not None:
        for state in states:
          all_macros.append(self._build_macros(state))
      else:
        all_macros.append(self._build_macros(None))
    return all_macros
    

  def _build_macros(self,state=None):
    macros = {}
    macros["P"] = self.get_name(state)
    macros["ZNAM"] = self.get_state_names()[0]
    macros["ONAM"] = self.get_state_names()[1]
    macros["LOCA"] = self.card.get_location()
    macros["CH"] = "{0}".format(self.number)
    macros["ID"] = "{0}".format(self.id)
    macros["ZSV"] = self.get_alarm_state()[0]
    macros["OSV"] = self.get_alarm_state()[1]
    macros["INT"] = "{0}".format(self.get_integrator())
    macros["MASK"] = "{0}".format(self.get_mask(state))
    macros["TYPE"] = self.get_type()
    macros["CRATE"] = self.card.crate.get_full_location()
    macros["SLOT"] = self.card.get_slot_text()
    macros["DEVICE"] = self.get_name(state)
    macros["CHANNEL"] = "{0}".format(self.number)
    macros["DEVICE_BYP"] = self.name
    macros["APPID"] = "{0}".format(self.card.number)
    macros["IN_CN"] = self.has_fault(state)
    return macros

  def is_fast_eval(self):
    return self.evaluation

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
   ignore_condition: Links to an ignore condition that uses to channel to define if it should
                     be active
  """
  __tablename__ = 'digital_channels'
  __mapper_args__ = {'polymorphic_identity': 'digital_channel'}
  id = Column(Integer,ForeignKey('channels.id'), primary_key=True)
  z_name = Column(String, nullable=False)
  o_name = Column(String, nullable=False)
  monitored_pv = Column(String, nullable=False, default="") # for SoftChannels only
  wdog = Column(Boolean, nullable=False, default=False) # for SoftChannels only
  debounce = Column(Integer, nullable=False, default=10)
  alarm_state = Column(Integer,nullable=False,default=0)
  ignore_condition = relationship("IgnoreCondition", back_populates='digital_channel')

  def get_alarm_state(self):
    if int(self.alarm_state) == 0:
      return ['MAJOR','NO_ALARM']
    else:
      return ['NO_ALARM','MAJOR']

  def get_state_names(self):
    states = [self.z_name,self.o_name]
    return states

  def get_integrator(self):
    return 1

  def get_type(self):
    return "DIGITAL"

  def get_mask(self,state=None):
    return 1

  def get_name(self,name=None):
    return self.name

  def has_fault(self,state=None):
    return True

  
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
  offset = Column(Float,nullable=False,default=0)
  slope = Column(Float,nullable=False,default=1)
  egu = Column(String,nullable=False,default='raw')
  integrator = Column(Integer, nullable=False,default=0)
  wf_only = Column(Boolean, nullable=False, default=False) # for channels to be used for WF diagnostics only
  gain_bay = Column(Integer, nullable=True)
  gain_channel = Column(Integer,nullable=True)

  def get_alarm_state(self):
    return ["NO_ALARM","MAJOR"]

  def get_state_names(self):
    states = ["IS_OK","IS_EXCEEDED"]
    return states

  def get_device_prefix(self):
    split_name = self.name.split(":")[:-1 or None]
    return ':'.join(split_name)

  def get_device_attribute(self):
    attr = self.name.split(":")[-1 or None]
    return attr

  def get_integrator(self):
    return self.integrator

  def get_type(self):
    return "ANALOG"

  def get_mask(self,state):
    if state is not None:
      return state.mask
    else:
      return 1

  def get_name(self,state):
    if state is not None:
      return "{0}_{1}".format(self.name,state.get_pv_name())
    else:
      return self.name

  def has_fault(self,state):
    if state is not None:
      return True
    else:
      return False

  def get_fault_states(self):
    fis = self.fault_input
    if len(fis) == 0:
      return None
    elif len(fis) > 1:
      print("ERROR: Too Many Fault Inputs")
      return None
    else:
      fi = fis[0]
      states = fi.fault.fault_states
      ss = []
      for s in states:
        ss.append(s)
      return ss



