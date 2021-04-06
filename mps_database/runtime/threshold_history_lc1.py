from sqlalchemy import Column, Integer, String, ForeignKey, Float, DateTime, func
from sqlalchemy.orm import relationship, backref
from mps_database.runtime import RuntimeBase
import datetime

class ThresholdHistoryLc1(RuntimeBase):
  """
  Threshold History LCLS-I class (thresholds history table)

  Properties:
    i[0-3]_[l|h]: last LCLS-I threshold set

    user: who changed the threshold
    date: when
    reason: why
    device_id: points to the device that owns this threshold
  """
  __tablename__ = 'thresholds_history_lc1'
  id = Column(Integer, primary_key=True)
  i0_l = Column(Float, default=0.0)
  i1_l = Column(Float, default=0.0)
  i2_l = Column(Float, default=0.0)
  i3_l = Column(Float, default=0.0)

  i0_h = Column(Float, default=0.0)
  i1_h = Column(Float, default=0.0)
  i2_h = Column(Float, default=0.0)
  i3_h = Column(Float, default=0.0)

  user = Column(String, nullable=False)
  date = Column(DateTime(timezone=True), server_default=func.now())
  reason = Column(String, nullable=False)
  device_id = Column(Integer, nullable=False)
