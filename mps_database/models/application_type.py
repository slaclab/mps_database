from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
from mps_database.models import Base

class ApplicationType(Base):
  """
  ApplicationType (application_card_types table)

  Describe an application card type that physically takes one slot. An 
  ApplicationCard is an ATCA carrier card with (or without) AMCs.

  It has a defined number of digital and analog channels, as described
  by the DigitalChannel class (digital_channels table) and 
  AnalogChannel class (analog_channels table).

  Properties:
   id: unique application card type identifier
   name: Currently, support 'MPS Analog','BCM','BLEN','Wire Scanner','LLRF','RTM Digital','MPS Digital'
   analog_channel_count: number of analog channels
   digital_channel_count: number of digital channels
   double_slot: indicates if this application card type uses two slots
   i.e. it really is composed of two cards (FIXME: not implemented yet, only added to comments)

  Relationships:
   cards: which ApplicationCards (application_cards table) are of this type
  """
  __tablename__ = 'application_card_types'
  id = Column(Integer, primary_key=True)
  name = Column(String, nullable=False, unique=True)
  num_integrators = Column(Integer,nullable=True)
  analog_channel_count = Column(Integer, nullable=False)
  digital_channel_count = Column(Integer, nullable=False)
  software_channel_count = Column(Integer, nullable=False)
  cards = relationship("ApplicationCard", back_populates='type')

  def get_integrator(self,fault=None):
    integrator = None
    if self.num_integrators > 0:
      if fault == None:
        return 0
      else:
        name = fault.split(':')[-1]
        if name == 'TMIT':
          return 0
        elif name == 'X':
          return 1
        elif name == 'Y':
          return 2
        else:
          return 0
  
  #@validates('cards')
  #def validate_cards(self, key, card):
  #  if self.digital_channel_count < len(card.channels.digital_channels):
  #    raise ValueError("Card cannot have a type with digital_channel_count < the number of digital_channels connected to the card.")
    
  #  if self.digital_out_channel_count < len(card.channels.digital_out_channels):
  #    raise ValueError("Card cannot have a type with digital_out_channel_count < the number of digital_out_channels connected to the card.")
  #  
  #  if self.analog_channel_count < len(card.channels.analog_channels):
  #    raise ValueError("Card cannot have a type with analog_channel_count < the number of analog_channels connected to the card.")
  #  return card

