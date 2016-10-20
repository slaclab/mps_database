from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship, backref
from models import Base
from .allowed_class import AllowedClass

class IgnoreCondition(Base):
  """
  IgnoreCondition class (ignore_conditions table)

  References:
    fault_state_id: 
    condition_id: 
  """
  __tablename__ = 'ignore_conditions'
  id = Column(Integer, primary_key=True)
  condition_id = Column(Integer, ForeignKey('conditions.id'), nullable=False)
  fault_state_id = Column(Integer, ForeignKey('fault_states.id'), nullable=False)
