from sqlalchemy import Column, Integer, String, ForeignKey, Float, Boolean
from sqlalchemy.orm import relationship, backref
from runtime import RuntimeBase

class ThresholdAlt2(RuntimeBase):
  """
  Threshold class (thresholds table)

  Properties:
    i[0..3]_[l|h]: threshold value
    i[0..3]_[l|h]_active: tells whether threshold has been set (many
                          thresholds won't be used). This prevents unused
                          thresholds from being restored to IOCs at boot time

  References:
    device_id: points to the device that owns this threshold
  """
  __tablename__ = 'thresholds_alt2'
  id = Column(Integer, primary_key=True)
  i0_l = Column(Float, default=0.0)
  i1_l = Column(Float, default=0.0)
  i2_l = Column(Float, default=0.0)
  i3_l = Column(Float, default=0.0)

  i0_h = Column(Float, default=0.0)
  i1_h = Column(Float, default=0.0)
  i2_h = Column(Float, default=0.0)
  i3_h = Column(Float, default=0.0)

  i0_l_active = Column(Boolean, default=False)
  i1_l_active = Column(Boolean, default=False)
  i2_l_active = Column(Boolean, default=False)
  i3_l_active = Column(Boolean, default=False)

  i0_h_active = Column(Boolean, default=False)
  i1_h_active = Column(Boolean, default=False)
  i2_h_active = Column(Boolean, default=False)
  i3_h_active = Column(Boolean, default=False)

  device_id = Column(Integer)
  device = relationship("Device", uselist=False, back_populates="threshold_alt2")
