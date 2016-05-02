from sqlalchemy import Column, Integer, Float, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship, backref
from models import Base

class ThresholdFault(Base):
  __tablename__ = 'threshold_faults'
  id = Column(Integer, primary_key=True)
  name = Column(String, nullable=False)
  analog_device_id = Column(Integer, ForeignKey('analog_devices.id'), nullable=False)
  threshold = Column(Float, nullable=False)
  #If greater_than is true, a value larger than the threshold will generate a fault.
  #If greater_than is false, a value smaller than the threshold will generate a fault.
  greater_than = Column(Boolean, nullable=False)
  threshold_fault_state = relationship("ThresholdFaultState", uselist=False, backref="threshold_fault")
  
  @property
  def less_than(self):
    return not self.greater_than