from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship, backref, validates
from mps_database.models import Base

class ApplicationCard(Base):
  """
  ApplicationCard class (application_cards table)

  Defines an application card, by specifying its type and location (which 
  crate and slot).

  Properties:
   number: global ID
   slot: number of slot within the ATCA crate where it is installed
   
  References:
   crate_id: specifies the crate that contains this card
   type_id: specifies the type of this card (e.g. Mixed Mode Link Node type)

  Relationships:
   digital_channels: there are zero or more entries in the
                     digital_channels table pointing to an application_card
                     entry.
   digital_out_channels: 
   analog_channels: there are zero or more entries in the
                    digital_channels table pointing to an application_card
                    entry.
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
