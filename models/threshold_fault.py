from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, backref
from models import Base

class ThresholdFault(Base):
  __tablename__ = 'threshold_faults'
  id = Column(Integer, primary_key=True)
  name = Column(String, nullable=False)
  analog_device_id = Column(Integer, ForeignKey('analog_devices.id'), nullable=False)
  threshold_fault_states = relationship("ThresholdFaultState", backref='threshold_fault')