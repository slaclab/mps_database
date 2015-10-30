from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.orm import relationship, backref
from models import Base

class Fault(Base):
  __tablename__ = 'faults'
  id = Column(Integer, primary_key=True)
  name = Column(String, unique=True, nullable=False)
  description = Column(String, nullable=True)
  states = relationship("FaultState", backref='fault')
  inputs = relationship("FaultInput", backref='fault')