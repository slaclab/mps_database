from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, backref
from models import Base

class ThresholdValueMap(Base):
  __tablename__ = 'threshold_value_maps'
  id = Column(Integer, primary_key=True)
  description = Column(String)
  values = relationship("ThresholdValue", backref='threshold_value_map')
  device_types = relationship("AnalogDeviceType", backref='threshold_value_map')