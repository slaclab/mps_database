from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship, backref
from models import Base
from .allowed_class import AllowedClass

class IgnoreCondition(Base):
  """
  IgnoreCondition class (ignore_conditions table)

  An IgnoreCondition defines when a certain AnalogDevice or a specific FaultState 
  of an AnalogDevice must ignored if the specified Condition is true.

  References:
    condition_id: if this condition is true than the fault_state or the analog_device
                  have faults ignored.
    fault_state_id: fault_state to be ignored (only used by EIC)
    analog_device_id: analog_device to be ignored.
  """
  __tablename__ = 'ignore_conditions'
  id = Column(Integer, primary_key=True)
  condition_id = Column(Integer, ForeignKey('conditions.id'), nullable=False)
  fault_state_id = Column(Integer, ForeignKey('fault_states.id'))
  analog_device_id = Column(Integer, ForeignKey('analog_devices.id'), nullable=False)
