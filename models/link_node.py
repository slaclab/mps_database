from sqlalchemy import Column, Integer
from sqlalchemy.orm import relationship
from models import Base
class LinkNode(Base):
  __tablename__ = 'link_nodes'
  id = Column(Integer, primary_key=True)
  number = Column(Integer, unique=True, nullable=False)
  cards = relationship("LinkNodeCard", backref='link_node')
  
