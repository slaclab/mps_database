from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
from models import Base

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
   number: part number
   name: e.g. Mixed Mode Link Node (one digital and one analog AMC)
   analog_channel_count: number of analog channels
   analog_channel_size: number of bits used by each analog channel
   digital_channel_count: number of digital channels
   digital_channel_size: number of bits used by each digital channel
   digital_out_channel_count
   digital_out_channel_size
   double_slot: indicates if this application card type uses two slots
   i.e. it really is composed of two cards (FIXME: not implemented yet, only added to comments)

  Relationships:
   cards: which ApplicationCards (application_cards table) are of this type
  """
  __tablename__ = 'application_card_types'
  id = Column(Integer, primary_key=True)
  number = Column(Integer, nullable=False, unique=True)
  name = Column(String, nullable=False, unique=True)
  analog_channel_count = Column(Integer, nullable=False)
  analog_channel_size = Column(Integer, nullable=False)
  digital_channel_count = Column(Integer, nullable=False)
  digital_channel_size = Column(Integer, nullable=False)
  digital_out_channel_count = Column(Integer, nullable=False)
  digital_out_channel_size = Column(Integer, nullable=False)
  cards = relationship("ApplicationCard", backref='type')
  
  @validates('cards')
  def validate_cards(self, key, card):
    if self.digital_channel_count < len(card.digital_channels):
      raise ValueError("Card cannot have a type with digital_channel_count < the number of digital_channels connected to the card.")
    
    if self.digital_out_channel_count < len(card.digital_out_channels):
      raise ValueError("Card cannot have a type with digital_out_channel_count < the number of digital_out_channels connected to the card.")
    
    if self.analog_channel_count < len(card.analog_channels):
      raise ValueError("Card cannot have a type with analog_channel_count < the number of analog_channels connected to the card.")
    return card
  
  @validates('digital_channel_count')
  def validate_digital_channel_count(self, key, new_count):
    self.validate_positive_channel_count('digital', new_count)
    
    #This is slow and bad.
    for c in self.cards:
      if len(c.digital_channels) > new_count:
        raise ValueError("New number of channels would not be compatible with existing card(s).")
    
    return new_count
  
  @validates('digital_out_channel_count')
  def validate_digital_out_channel_count(self, key, new_count):
    self.validate_positive_channel_count('digital_out', new_count)
    
    #This is slow and bad.
    for c in self.cards:
      if len(c.digital_out_channels) > new_count:
        raise ValueError("New number of channels would not be compatible with existing card(s).")
    
    return new_count
  
  @validates('analog_channel_count')
  def validate_analog_channel_count(self, key, new_count):
    self.validate_positive_channel_count('analog', new_count)
    
    #This is slow and bad.
    for c in self.cards:
      if len(c.analog_channels) > new_count:
        raise ValueError("New number of channels would not be compatible with existing card(s).")
    
    return new_count
  
  
  def validate_positive_channel_count(self, chan_type, new_count):
    if new_count < 0:
      raise ValueError("Type must have a {type} channel count >= 0.".format(type=chan_type))    
    return new_count
  
  @validates('channel_size')
  def validate_channel_size(self, key, new_size):
    if new_size < 0:
      raise ValueError("Channel size must be >= 0.")
    return new_size
