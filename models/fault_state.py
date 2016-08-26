from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, backref
from models import Base
from .allowed_class import AllowedClass

class FaultState(Base):
  """
  FaultState class (fault_states table)

  Properties:
    type: either digital_fault_state or analog_fault_state

  Relationships:
    allowed_classes: list of beam allowed classes for this fault
  """
  __tablename__ = 'fault_states'
  id = Column(Integer, primary_key=True)
  discriminator = Column('type', String(50))
  __mapper_args__ = {'polymorphic_on': discriminator}
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

class DigitalFaultState(FaultState):
  """
  DigitalFaultState class (digital_fault_states table)

  Properties:
    value: bit combination that represents this fault
    name: fault name (e.g. Out, In, Broken...)

  References:
    fault_id: points to the Fault that can generate this state
  """
  __tablename__ = 'digital_fault_states'
  __mapper_args__ = {'polymorphic_identity': 'digital_fault_state'}
  id = Column(Integer, ForeignKey('fault_states.id'), primary_key=True)
  value = Column(Integer, nullable=False)
  name = Column(String, nullable=False)
  fault_id = Column(Integer, ForeignKey('faults.id'), nullable=False)

class ThresholdFaultState(FaultState):
  """
  ThresholdFaultState class (threshold_fault_states table)

  References:
    fault_id: points to the ThresholdFault (analog fault) that can
              generate this state
  """
  __tablename__ = 'threshold_fault_states'
  __mapper_args__ = {'polymorphic_identity': 'threshold_fault_state'}
  id = Column(Integer, ForeignKey('fault_states.id'), primary_key=True)
  threshold_fault_id = Column(Integer, ForeignKey('threshold_faults.id'), nullable=False)
