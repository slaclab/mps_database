from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship, backref
from models import Base

class LinkNodeCard(Base):
  __tablename__ = 'link_node_cards'
  id = Column(Integer, primary_key=True)
  number = Column(Integer, nullable=False)
  link_node_id = Column(Integer, ForeignKey('link_nodes.id'), nullable=False)
  type_id = Column(Integer, ForeignKey('link_node_card_types.id'), nullable=False)
  channels = relationship("LinkNodeChannel", backref='card')