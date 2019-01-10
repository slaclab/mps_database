from sqlalchemy import Column, Integer, String, ForeignKey, Float
from sqlalchemy.orm import relationship, backref
from runtime import RuntimeBase

class ThresholdIdl(RuntimeBase):
  """
  Threshold class (thresholds table)

  Properties:
    l: low idle threshold
    h: high idle threshold

  References:
    device_id: points to the device that owns this threshold
  """
  __tablename__ = 'thresholds_idl'
  id = Column(Integer, primary_key=True)
  l = Column(Float, default=0.0)
  h = Column(Float, default=0.0)

  device_id = Column(Integer)
  device = relationship("Device", uselist=False, back_populates="threshold_idl")
