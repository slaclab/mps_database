from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship, backref
from models import Base
from .allowed_class import AllowedClass

class FaultState(Base):
  """
  FaultState class (fault_states table)

  Properties:
    default: defines if this state is the default for the fault, i.e. if other digital
             states are not faulted, it defaults to this one


  Relationships:
    allowed_classes: list of beam allowed classes for this fault
  """
  __tablename__ = 'fault_states'
  id = Column(Integer, primary_key=True)
  allowed_classes = relationship("AllowedClass", backref='fault_state')
  ignore_conditions = relationship("IgnoreCondition", backref='fault_state')
  condition_inputs = relationship("ConditionInput", backref='fault_state')
  default = Column(Boolean, nullable=False, default=False)
  fault_id = Column(Integer, ForeignKey('faults.id'), nullable=False)
  device_state_id = Column(Integer, ForeignKey('device_states.id'), nullable=False)

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

