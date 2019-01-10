from sqlalchemy import Column, Integer, String, ForeignKey, Float, DateTime, func
from sqlalchemy.orm import relationship, backref
from runtime import RuntimeBase
import datetime

class ThresholdHistoryLc1(RuntimeBase):
  """
  Threshold History LCLS-I class (thresholds history table)

  Properties:
    l: new low LCLS-I threshold
    h: new high LCLS-I threshold
    user: who changed the threshold (either l/h or both)
    date: when
    reason: why
    device_id: points to the device that owns this threshold
  """
  __tablename__ = 'thresholds_history_lc1'
  id = Column(Integer, primary_key=True)
  l = Column(Float, default=0.0)
  h = Column(Float, default=0.0)
  user = Column(String, nullable=False)
  date = Column(DateTime(timezone=True), server_default=func.now())
  reason = Column(String, nullable=False)
  device_id = Column(Integer, nullable=False)
