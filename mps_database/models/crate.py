from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, validates
from mps_database.models import Base

class Crate(Base):
  """
  Crate class (crates table)
  
  Describes an ATCA crate, properties are:
    crate_id: number that identifies the crate connected to a CPU. The CPU is
              the hostname where the link_node_id runs. There maybe one or
              more crates connected to one CPU (additional information at:
              https://confluence.slac.stanford.edu/display/ppareg/EED+ATCA+Shelf+manager%27s+shelfaddress+naming+convention
              The crate_id is globally unique, it is unique among the crates
              connected to one CPU.
    shelf_number: 
    num_slots: number of slots available (usually 2 or 7)
    location: string containing area where this crate is installed (e.g. LKG02, LKA01)
    sector: string containing sector where this crate is installed (e.g. LI00, LI10, LTU, BSY)
    rack: string containing the rack identifier (usually a number)
    elevation: elevation within the rack

  Relationships:
    cards: each ApplicationCard has a reference to a crate 

  References:
    link_node_id: points to the link node (in slot 2) for this crate. There may be more
                  link nodes connected to other cards in the same crate (non-slot 2)
  """
  __tablename__ = 'crates'
  id = Column(Integer, primary_key=True)
  crate_id = Column(Integer, nullable=False)
  shelf_number = Column(Integer, nullable=False)
  num_slots = Column(Integer, nullable=False)
  location = Column(String, nullable=False)
  sector = Column(String, nullable=False)
  rack = Column(String, nullable=False)
  elevation = Column(Integer, nullable=False, default=0)
  cards = relationship("ApplicationCard", backref='crate')
  link_nodes = relationship("LinkNode", backref='crate')

  def get_name(self):
    return self.location #+ '-' + self.rack #+ str(self.elevation)
  
  @validates('cards')
  def validate_card(self, key, new_card):
    """
    When a new card is added make sure there are no conflicts,
    such as is the slot available and is the slot number valid.
    """
    #Ensure the crate won't be full after adding the new card
# This test is not correct because on the same slot there may be amc cards - need to add other type of check    
#    if len(self.cards)+1 > self.num_slots:
#      raise ValueError("Crate cannot have more cards than num_slots.")
    
    #Ensure the slot exists
    if new_card.slot_number > self.num_slots:
      print(("Card {c} is in slot {s1} but there are only {s2} slots available".format(c=new_card.number, s1=new_card.slot_number, s2= self.num_slots)))
      raise ValueError("Card cannot use slot_number > num_slots.")
    
    if new_card.slot_number == None:
      raise ValueError('Slot number is None (card "{}")'.format(new_card.name))

    if new_card.slot_number < 0:
      raise ValueError('Slot number must be positive (slot_number={0}).'.format(new_card.slot_number))
    
    #Ensure the slot isn't taken
    if [new_card.slot_number, new_card.amc] in [[c.slot_number, c.amc] for c in self.cards]:
      print(("Slot is already taken by another card. New card:" + str(new_card.number) + " New amc:" + str(new_card.slot_number) + "; existing card: " + str(c.number) + " amc: " + str(c.slot_number)))
      raise ValueError("Slot is already taken by another card. New card:" + new_card.name + " New amc:" + str(new_card.amc) + "; existing card: " + c.name + " amc: " + str(c.amc))
    
    return new_card
  
  @validates('num_slots')
  def validate_num_slots(self, key, new_num_slots):
    """
    Make sure the number of slots is enough to hold all the cards
    (ApplicationCard class) that are in the crate.
    """
    #Cast new_num_slots as an integer
    new_num_slots = int(new_num_slots)

    #Ensure there are enough slots to fit all the installed cards.
    if new_num_slots < len(self.cards):
      raise ValueError("num_slots ({num_slots}) must be >= than the number of cards in this crate ({num_cards}).".format(num_slots=new_num_slots, num_cards=len(self.cards)))
    
    #Ensure the installed cards are still in valid slots
    for c in self.cards:
      if c.slot_number > new_num_slots:
        raise ValueError("new value for num_slots would invalidate a currently installed card.")
    
    return new_num_slots
    
    
