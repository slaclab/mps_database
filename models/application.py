from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship, backref
from models import Base

class Application(Base):
  __tablename__ = 'applications'
  id = Column(Integer, primary_key=True)
  global_id = Column(Integer, nullable=False, unique=True)
  name = Column(String, unique=True, nullable=False)
  description = Column(String, nullable=True)
  devices = relationship("Device", backref='application')

