from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
from models import Base
class ApplicationCardType(Base):
  __tablename__ = 'application_card_types'
  id = Column(Integer, primary_key=True)
  number = Column(Integer, nullable=False, unique=True)
  name = Column(String, nullable=False, unique=True)
  channel_count = Column(Integer, nullable=False)
  channel_size = Column(Integer, nullable=False)
  cards = relationship("ApplicationCard", backref='type')
  
  @validates('cards')
  def validate_cards(self, key, card):
    if self.channel_count < len(card.channels):
      raise ValueError("Card cannot have a type with channel_count < the number of channels connected to the card.")
    return card
  
  @validates('channel_count')
  def validate_channel_count(self, key, new_count):
    if new_count < 1:
      raise ValueError("Type must have a channel count >= 1.")
    
    #This is slow and bad.
    for c in self.cards:
      if len(c.channels) > new_count:
        raise ValueError("New number of channels would not be compatible with existing card(s).")
    
    return new_count
  
  @validates('channel_size')
  def validate_channel_size(self, key, new_size):
    if new_size < 1:
      raise ValueError("Channel size must be >= 1.")