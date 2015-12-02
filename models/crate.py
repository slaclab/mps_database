from sqlalchemy import Column, Integer
from sqlalchemy.orm import relationship
from models import Base

class Crate(Base):
  __tablename__ = 'crates'
  id = Column(Integer, primary_key=True)
  number = Column(Integer, unique=True, nullable=False)
  num_slots = Column(Integer, nullable=False)
  cards = relationship("ApplicationCard", backref='crate')