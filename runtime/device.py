from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, backref
from runtime import RuntimeBase

class Device(RuntimeBase):
  """
  Threshold class (thresholds table)

  Properties:
    mpsdb_id: device id in the static mps database
    mpsdb_name: name of device from the static mps database
  """
  __tablename__ = 'devices'
  id = Column(Integer, primary_key=True)
  mpsdb_id = Column(Integer, nullable=False)
  mpsdb_name = Column(String, unique=True, nullable=False)
  threshold0_id = Column(Integer, ForeignKey('thresholds0.id'))
  threshold1_id = Column(Integer, ForeignKey('thresholds1.id'))
  threshold2_id = Column(Integer, ForeignKey('thresholds2.id'))
  threshold3_id = Column(Integer, ForeignKey('thresholds3.id'))
  threshold0 = relationship("Threshold0", back_populates="device")
  threshold1 = relationship("Threshold1", back_populates="device")
  threshold2 = relationship("Threshold2", back_populates="device")
  threshold3 = relationship("Threshold3", back_populates="device")

  threshold_alt0_id = Column(Integer, ForeignKey('thresholds_alt0.id'))
  threshold_alt1_id = Column(Integer, ForeignKey('thresholds_alt1.id'))
  threshold_alt2_id = Column(Integer, ForeignKey('thresholds_alt2.id'))
  threshold_alt3_id = Column(Integer, ForeignKey('thresholds_alt3.id'))
  threshold_alt0 = relationship("ThresholdAlt0", back_populates="device")
  threshold_alt1 = relationship("ThresholdAlt1", back_populates="device")
  threshold_alt2 = relationship("ThresholdAlt2", back_populates="device")
  threshold_alt3 = relationship("ThresholdAlt3", back_populates="device")
