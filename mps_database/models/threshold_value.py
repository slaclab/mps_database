from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship, backref
from mps_database.models import Base

class ThresholdValue(Base):
  """
  ThresholdValue class (threshold_values table)

  This class contains the mapping from compressed analog values to 
  floating point values. The analog data in transmitted from Link Nodes
  to the Central Node using up to 12-bits, i.e. a compressed version
  of the actual analog value. 

  Properties:
    threshold: compressed threshold value 
    value: actual analog value

  References:
    threshold_value_map_id: this ThresholdValue belongs to a map for a
                            given AnalogDeviceType.

  Relationships:
    threshold_faults: list of threshold_faults that occur when crossing
                      this threshold
  """
  __tablename__ = 'threshold_values'
  id = Column(Integer, primary_key=True)
  threshold = Column(Integer, nullable=False)
  value = Column(Float, nullable=False)
  threshold_value_map_id = Column(Integer, ForeignKey('threshold_value_maps.id'), nullable=False)
  threshold_faults = relationship("ThresholdFault", backref='threshold_value')
