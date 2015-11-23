from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, backref
from models import Base

class BeamClass(Base):
  __tablename__ = 'beam_classes'
  id = Column(Integer, primary_key=True)
  number = Column(Integer, nullable=False, unique=True)
  name = Column(String, nullable=False)
  allowed_classes = relationship("AllowedClass", backref='beam_class')