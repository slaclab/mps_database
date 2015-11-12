from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship, backref
from models import Base

class AllowedClass(Base):
  __tablename__ = 'allowed_classes'
  id = Column(Integer, primary_key=True)
  fault_state_id = Column(Integer, ForeignKey('fault_states.id'), nullable=False)
  mitigation_device_id = Column(Integer, ForeignKey('mitigation_devices.id'), nullable=False)
  class_id  = Column(Integer, ForeignKey('beam_classes.id'), nullable=False)