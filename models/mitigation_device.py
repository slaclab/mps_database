from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, backref
from models import Base

class MitigationDevice(Base):
  """
  MitigationDevice class (mitigation_devices table)

  Properties:
    name: mitigation device name (e.g. AOM)
    
  Relationships:
    allowed_classes: list of AllowedClasses for this mitigation device
  """
  __tablename__ = 'mitigation_devices'
  id = Column(Integer, primary_key=True)
  name = Column(String, nullable=False, unique=True)
  allowed_classes = relationship("AllowedClass", backref='mitigation_device')
