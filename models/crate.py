from sqlalchemy import Column, Integer
from sqlalchemy.orm import relationship, validates
from models import Base

class Crate(Base):
  __tablename__ = 'crates'
  id = Column(Integer, primary_key=True)
  number = Column(Integer, unique=True, nullable=False)
  num_slots = Column(Integer, nullable=False)
  cards = relationship("ApplicationCard", backref='crate')
  
  @validates('cards')
  def validate_card(self, key, new_card):
    #Ensure the crate won't be full after adding the new card
    if len(self.cards)+1 > self.num_slots:
      raise ValueError("Crate cannot have more cards than num_slots.")
    
    #Ensure the slot exists
    if new_card.slot_number > self.num_slots:
      raise ValueError("Card cannot use slot_number > num_slots.")
    
    if new_card.slot_number < 0:
      raise ValueError("Slot number must be positive.")
    
    #Ensure the slot isn't taken
    if new_card.slot_number in [c.slot_number for c in self.cards]:
      raise ValueError("Slot is already taken by another card.")
    return cards
  
  @validates('num_slots')
  def validate_num_slots(self, key, new_num_slots):
    #Ensure there are enough slots to fit all the installed cards.
    if new_num_slots < len(self.cards):
      raise ValueError("num_slots ({num_slots}) must be >= than the number of cards in this crate ({num_cards}).".format(num_slots=new_num_slots, num_cards=len(self.cards)))
    
    #Ensure the installed cards are still in valid slots
    for c in self.cards:
      if c.slot_number > new_num_slots:
        raise ValueError("new value for num_slots would invalidate a currently installed card.")
    
    return new_num_slots
    
    