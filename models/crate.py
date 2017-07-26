from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship, validates
from models import Base

class Crate(Base):
  """
  Crate class (crates table)
  
  Describes an ATCA crate, properties are:
    number: crate number (property or serial number)
    self_number: 
    num_slots: number of slots available (usually 2 or 7)
    location: string containing sector/area where this crate is installed (e.g. LKG02, LKA01)
    rack: string containing the rack identifier (usually a number)
    elevation: elevation within the rack

  Relationships:
    cards: each ApplicationCard has a reference to a crate 
  """
  __tablename__ = 'crates'
  id = Column(Integer, primary_key=True)
  number = Column(Integer, unique=True, nullable=False)
  shelf_number = Column(Integer, nullable=False)
  num_slots = Column(Integer, nullable=False)
  location = Column(String, nullable=False)
  rack = Column(String, nullable=False)
  elevation = Column(Integer, nullable=False, default=0)
  cards = relationship("ApplicationCard", backref='crate')
  
  @validates('cards')
  def validate_card(self, key, new_card):
    """
    When a new card is added make sure there are no conflicts,
    such as is the slot available and is the slot number valid.
    """
    #Ensure the crate won't be full after adding the new card
    if len(self.cards)+1 > self.num_slots:
      raise ValueError("Crate cannot have more cards than num_slots.")
    
    #Ensure the slot exists
    if new_card.slot_number > self.num_slots:
      raise ValueError("Card cannot use slot_number > num_slots.")
    
    if new_card.slot_number < 0:
      raise ValueError("Slot number must be positive.")
    
    #Ensure the slot isn't taken
    if [new_card.slot_number, new_card.amc] in [[c.slot_number, c.amc] for c in self.cards]:
      raise ValueError("Slot is already taken by another card. New card:" + new_card.name + "; existing card: " + c.name)
    
    return new_card
  
  @validates('num_slots')
  def validate_num_slots(self, key, new_num_slots):
    """
    Make sure the number of slots is enough to hold all the cards
    (ApplicationCard class) that are in the crate.
    """
    #Ensure there are enough slots to fit all the installed cards.
    if new_num_slots < len(self.cards):
      raise ValueError("num_slots ({num_slots}) must be >= than the number of cards in this crate ({num_cards}).".format(num_slots=new_num_slots, num_cards=len(self.cards)))
    
    #Ensure the installed cards are still in valid slots
    for c in self.cards:
      if c.slot_number > new_num_slots:
        raise ValueError("new value for num_slots would invalidate a currently installed card.")
    
    return new_num_slots
    
    
