from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, backref
from models import Base

class MitigationDevice(Base):
  __tablename__ = 'mitigation_devices'
  id = Column(Integer, primary_key=True)
  name = Column(String, nullable=False, unique=True)
  allowed_classes = relationship("AllowedClass", backref='mitigation_device')