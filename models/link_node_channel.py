from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship, backref
from models import Base

class LinkNodeChannel(Base):
  __tablename__ = 'link_node_channels'
  id = Column(Integer, primary_key=True)
  number = Column(Integer, nullable=False)
  card_id = Column(Integer, ForeignKey('link_node_cards.id'), nullable=False)
  device_input = relationship("DeviceInput", uselist=False, backref="channel")