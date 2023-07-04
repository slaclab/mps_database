from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from mps_database.models import Base

class BeamDestination(Base):
  """
  BeamDestination class (beam_destinations table)

  properties:
    name: linac, sxu, hxu, diag0
    mask: destination mask (i.e. 0x1 is Laser, 0x2 is DIAG0, 0x4 is SC_BSYD, etc.)
    
  relationships:
    mitigations: list of Mitigation for this beam destination
  """
  __tablename__ = 'beam_destinations'
  id = Column(Integer, primary_key=True)
  name = Column(String, nullable=False, unique=True)
  mask = Column(Integer, nullable=False, unique=True)
  mitigations = relationship("Mitigation",back_populates="beam_destination")
