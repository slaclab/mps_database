from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, backref
from models import Base
from .allowed_class import AllowedClass

class FaultState(Base):
  __tablename__ = 'fault_states'
  id = Column(Integer, primary_key=True)
  value = Column(Integer, nullable=False)
  name = Column(String, nullable=False)
  fault_id = Column(Integer, ForeignKey('faults.id'), nullable=False)
  allowed_classes = relationship("AllowedClass", backref='fault_state')
  
  def add_allowed_class(self, beam_class, mitigation_device):
    ac = AllowedClass()
    ac.beam_class = beam_class
    ac.mitigation_device = mitigation_device
    self.allowed_classes.append(ac)
    return ac
  
  def add_allowed_classes(self, beam_classes, mitigation_device):
    acs = []
    for c in beam_classes:
      acs.append(self.add_allowed_class(c, mitigation_device))
    return acs
      