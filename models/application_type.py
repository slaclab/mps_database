from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
from models import Base
class ApplicationType(Base):
  __tablename__ = 'application_card_types'
  id = Column(Integer, primary_key=True)
  number = Column(Integer, nullable=False, unique=True)
  name = Column(String, nullable=False, unique=True)
  analog_channel_count = Column(Integer, nullable=False)
  analog_channel_size = Column(Integer, nullable=False)
  digital_channel_count = Column(Integer, nullable=False)
  digital_channel_size = Column(Integer, nullable=False)
  cards = relationship("ApplicationCard", backref='type')
  
  @validates('cards')
  def validate_cards(self, key, card):
    if self.digital_channel_count < len(card.digital_channels):
      raise ValueError("Card cannot have a type with digital_channel_count < the number of digital_channels connected to the card.")
    
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