from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship, backref, validates
from models import Base

class ApplicationCard(Base):
  __tablename__ = 'application_cards'
  id = Column(Integer, primary_key=True)
  number = Column(Integer, nullable=False)
  slot_number = Column(Integer, nullable=False)
  crate_id = Column(Integer, ForeignKey('crates.id'), nullable=False)
  type_id = Column(Integer, ForeignKey('application_card_types.id'), nullable=False)
  channels = relationship("Channel", backref='card')
  
  @validates('channels')
  def validate_channel(self, key, new_channel):
    if self.type and len(self.channels)+1 > self.type.channel_count:
      raise ValueError("Number of channels on this card cannot exceed the card type's channel count ({count})".format(count=self.type.channel_count))
    
    if self.type and new_channel.number >= self.type.channel_count:
      raise ValueError("For this card's type, channel number must be < {count}".format(count=self.type.channel_count))
    
    if new_channel.number < 0:
      raise ValueError("Channel number must be positive.")
    
    #Ensure the channel isn't taken
    if new_channel.number in [c.number for c in self.channels]:
      raise ValueError("Channel number {num} is already taken by an existing channel.".format(num=new_channel.number))
    
    return new_channel
  
  @validates('slot_number')
  def validate_slot_number(self, key, new_slot):
    if self.crate and new_slot > self.crate.num_slots:
      raise ValueError("Slot number must be <= the number of slots in the crate ({count})".format(count=self.crate.num_slots))
    
    if self.crate and new_slot in [c.number for c in self.crate.cards]:
      raise ValueError("This slot is already taken by another card in the crate.")
    
    return new_slots