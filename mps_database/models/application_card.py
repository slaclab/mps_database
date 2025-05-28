from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship
from mps_database.models import Base

class ApplicationCard(Base):
  """
  ApplicationCard class (application_cards table)

  Defines an application card, by specifying its type and location (which 
  crate and slot).

  Properties:
   number: global ID
   slot: number of slot within the ATCA crate where it is installed
   location: this is the location field to generate ioc PVs (third field, e.g. MP02)
   
  References:
   crate_id: specifies the crate that contains this card
   type_id: specifies the type of this card (e.g. Mixed Mode Link Node type)

  Relationships:
   channels: collection of channels assigned to this card
  """
  __tablename__ = 'application_cards'
  id = Column(Integer, primary_key=True)
  number = Column(Integer, nullable=False,unique=True)
  crate_id = Column(Integer, ForeignKey('crates.id'), nullable=False)
  crate = relationship('Crate',back_populates='cards')
  type = relationship('ApplicationType',back_populates='cards')
  type_id = Column(Integer, ForeignKey('application_card_types.id'), nullable=False)
  channels = relationship("Channel",order_by="Channel.number",back_populates='card')
  slot = Column(Integer, nullable=False)
  location = Column(String, nullable=True, unique=False)  

  def validate_channels(self,num):
    not_in_use = True
    if self.type.name == 'BPM':
      if len(self.channels) > (2*self.type.num_integrators)-1:
        not_in_use=False
    else:
      for ch in self.channels:
        if ch.number == int(num):
          not_in_use=False
    return not_in_use

  def is_mps_digital(self):
    if self.type.name == 'RTM Digital':
      return True
    elif self.type.name == 'MPS Digital':
      return True
    else:
      return False

  def is_mps_analog(self):
    if self.can_have_analog():
      if self.type.name == 'MPS Analog':
        return True
      else:
        return False

  def get_mps_prefix(self):
    if self.slot < 3:
      return '{0}:1'.format(self.crate.get_ln().get_mps_prefix())
    else:
      return '{0}:{1}'.format(self.crate.get_ln().get_mps_prefix(),self.slot)

  def can_have_analog(self):
    if self.type.analog_channel_count > 0:
      return True
    else:
      return False

  def can_have_digital(self):
    if self.type.digital_channel_count > 0:
      return True
    else:
      return False

  def can_have_software(self):
    if self.type.software_channel_count > 0:
      return True
    else:
      return False

  def get_num_integrators(self):
    return self.type.num_integrators

  def has_mps_ioc(self):
    has_mps_ioc = False
    if self.is_mps_digital():
      has_mps_ioc = True
    if self.slot > 2 and self.is_mps_analog():
      has_mps_ioc = True
    return has_mps_ioc

  def get_ioc_name(self):
    return 'sioc-{0}-{1}'.format(self.crate.area.lower(),self.location.lower())

  def get_central_node(self):
    lns = self.crate.link_node
    if len(lns) < 1:
      print("ERROR: No link node for card {0}".format(self.number))
      return Null
    if len(lns) > 1:
      print("ERROR: Too many link node for card {0}".format(self.number))
      return Null
    if len(lns) == 1:
      ln = lns[0]
      cn = ln.group.central_node
      return cn

  def get_real_slot(self):
    if self.slot < 2:
      return 2
    else:
      return self.slot

  def get_slot_text(self):
    if self.slot == 1:
      text = 'RTM'
    else: 
      text = '{0}'.format(self.slot)
    return text

  def get_bays_populated(self):
    chans = len(self.channels)
    if self.is_mps_digital():
      return 0
    elif self.type.name == "BCM" or self.type.name == "BLEN":
      return 1
    elif self.type.name == "LLRF" or self.type.name == "Wire Scanner":
      return 1
    elif self.type.name == "BPMS":
      if chans > 1:
        return 2
      else:
        return 1
    elif self.is_mps_analog():
      if chans > 2:
        return 2
      else:
        return 1
    else:
      print("ERROR: ard.get_bays_populated --> no card type found")
      return None

  def get_tpr(self):
    return "TPR:{0}:{1}:0".format(self.crate.area,self.location)

