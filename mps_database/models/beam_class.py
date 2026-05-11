from sqlalchemy import Column, Integer, String, ForeignKey, func
from sqlalchemy.orm import relationship, object_session
from mps_database.models import Base

class BeamClass(Base):
  """
  BeamClass class (beam_classes table)

  Describe all available beam classes.

  Properties:
    number: beam class identifier, starting at 1 for the beam with least
            power and increasing according to the power. This number is
            used to define which BeamClass to use in case of a fault.
    name: beam class name identifier
    integration_window: time window used by MPS to verify beam power
    min_period: minimum period between bunches
    total_charge: maximum charge within the integration window

  Relationships:
    mitigations: list of Mitigation that have this BeamClass
                     as the maximum allowed beam power
  """
  __tablename__ = 'beam_classes'
  id = Column(Integer, primary_key=True)
  number = Column(Integer, nullable=False, unique=True)
  name = Column(String, nullable=False)
  integration_window = Column(Integer, nullable=False)
  min_period = Column(Integer, nullable=False)
  total_charge = Column(Integer, nullable=False)
  mitigations = relationship("Mitigation",back_populates="beam_class")

  def get_name(self,report=False):
    session = object_session(self)
    max_beam_class = session.query(func.max(BeamClass.number)).one()[0]
    if self.number == max_beam_class:
      rval =  '-'
    else:
      rval = self.name
    if report:
      rval = rval.replace('_','\\_').replace('&','\\&').replace('%','\\%')
    return rval