from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, backref
from models import Base

class BeamClass(Base):
  """
  BeamClass class (beam_classes table)

  Describe all available beam classes.

  Properties:
    number: beam class identifier, starting at 1 for the beam with least
            power and increasing according to the power. This number is
            used to define which BeamClass to use in case of a fault.
    name: beam class name identifier
    description: short explanation for this beam class
    integration_window: time window used by MPS to verify beam power
    min_period: minimum period between bunches
    total_charge: maximum charge within the integration window

  Relationships:
    allowed_classes: list of AllowedClasses that have this BeamClass
                     as the maximum allowed beam power
  """
  __tablename__ = 'beam_classes'
  id = Column(Integer, primary_key=True)
  number = Column(Integer, nullable=False, unique=True)
  name = Column(String, nullable=False)
  description = Column(String, nullable=True)
  integration_window = Column(Integer)
  min_period = Column(Integer)
  total_charge = Column(Integer)
  allowed_classes = relationship("AllowedClass", backref='beam_class')
