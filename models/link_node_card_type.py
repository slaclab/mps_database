from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from models import Base
class LinkNodeCardType(Base):
  __tablename__ = 'link_node_card_types'
  id = Column(Integer, primary_key=True)
  name = Column(String, nullable=False, unique=True)
  channel_count = Column(Integer, nullable=False)
  cards = relationship("LinkNodeCard", backref='type')