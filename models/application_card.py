from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship, backref
from models import Base

class ApplicationCard(Base):
  __tablename__ = 'application_cards'
  id = Column(Integer, primary_key=True)
  number = Column(Integer, nullable=False)
  slot_number = Column(Integer, nullable=False)
  crate_id = Column(Integer, ForeignKey('crates.id'), nullable=False)
  type_id = Column(Integer, ForeignKey('application_card_types.id'), nullable=False)
  channels = relationship("Channel", backref='card')