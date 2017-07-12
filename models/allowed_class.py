from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship, backref
from models import Base

class AllowedClass(Base):
  """
  AllowedClass class (allowed_classes table)

  List of AllowedClasses for a given Fault (via fault_state_id)

  References:
    fault_state_id: the FaultState (Digital or Analog) for this AllowedClass
    mitigation_device_id: which mitigation device should be used for this 
    beam_class_id: the BeamClass allowed
  """
  __tablename__ = 'allowed_classes'
  id = Column(Integer, primary_key=True)
  fault_state_id = Column(Integer, ForeignKey('fault_states.id'), nullable=False)
  mitigation_device_id = Column(Integer, ForeignKey('mitigation_devices.id'), nullable=False)
  beam_class_id  = Column(Integer, ForeignKey('beam_classes.id'), nullable=False)
