from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, backref
from mps_database.models import Base

class BeamDestination(Base):
  """
  BeamDestination class (beam_destinations table)

  properties:
    name: linac, sxu, hxu, diag0
    description: main linac, soft x-ray undulator, hard x-ray undulator
    
  relationships:
    allowed_classes: list of allowedclasses for this beam destination
  """
  __tablename__ = 'beam_destinations'
  id = Column(Integer, primary_key=True)
  name = Column(String, nullable=False, unique=True)
  description = Column(String, nullable=False)
  destination_mask = Column(Integer, nullable=False, unique=True)
  allowed_classes = relationship("AllowedClass", backref='beam_destination')
  mitigation_devices = relationship("MitigationDevice", backref='beam_destination')
