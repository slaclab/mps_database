from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, backref
from models import Base

class FaultState(Base):
  __tablename__ = 'fault_states'
  id = Column(Integer, primary_key=True)
  value = Column(Integer, nullable=False)
  name = Column(String, nullable=False)
  fault_id = Column(Integer, ForeignKey('faults.id'), nullable=False)
  allowed_classes = relationship("AllowedClass", backref='fault_state')