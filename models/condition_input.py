from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, backref
from models import Base

class ConditionInput(Base):
  """
  ConditionInput class (condition_inputs table)

  Properties:
    bit_position: the position for the fault state within the condition value

  References:
    fault_state_id:
    condition_id:
  """
  __tablename__ = 'condition_inputs'
  id = Column(Integer, primary_key=True)
  bit_position = Column(Integer, nullable=False)
  fault_state_id = Column(Integer, ForeignKey('fault_states.id'), nullable=False)
  condition_id = Column(Integer, ForeignKey('conditions.id'), nullable=False)
