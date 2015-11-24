from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship, backref
from models import Base

class ThresholdValue(Base):
  __tablename__ = 'threshold_values'
  id = Column(Integer, primary_key=True)
  threshold = Column(Integer, nullable=False)
  value = Column(Float, nullable=False)
  threshold_value_map_id = Column(Integer, ForeignKey('threshold_value_maps.id'), nullable=False)