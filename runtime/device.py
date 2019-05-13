from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, backref
from runtime import RuntimeBase

class Device(RuntimeBase):
  """
  Device class

  Each instance contains the MPS database id and name of a device
  (analog or digital), and a list of current analog thresholds.

  Thresholds will be empty for digital devices.

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
  threshold4_id = Column(Integer, ForeignKey('thresholds4.id'))
  threshold5_id = Column(Integer, ForeignKey('thresholds5.id'))
  threshold6_id = Column(Integer, ForeignKey('thresholds6.id'))
  threshold7_id = Column(Integer, ForeignKey('thresholds7.id'))
  threshold0 = relationship("Threshold0", back_populates="device")
  threshold1 = relationship("Threshold1", back_populates="device")
  threshold2 = relationship("Threshold2", back_populates="device")
  threshold3 = relationship("Threshold3", back_populates="device")
  threshold4 = relationship("Threshold4", back_populates="device")
  threshold5 = relationship("Threshold5", back_populates="device")
  threshold6 = relationship("Threshold6", back_populates="device")
  threshold7 = relationship("Threshold7", back_populates="device")

  threshold_alt0_id = Column(Integer, ForeignKey('thresholds_alt0.id'))
  threshold_alt1_id = Column(Integer, ForeignKey('thresholds_alt1.id'))
  threshold_alt2_id = Column(Integer, ForeignKey('thresholds_alt2.id'))
  threshold_alt3_id = Column(Integer, ForeignKey('thresholds_alt3.id'))
  threshold_alt4_id = Column(Integer, ForeignKey('thresholds_alt4.id'))
  threshold_alt5_id = Column(Integer, ForeignKey('thresholds_alt5.id'))
  threshold_alt6_id = Column(Integer, ForeignKey('thresholds_alt6.id'))
  threshold_alt7_id = Column(Integer, ForeignKey('thresholds_alt7.id'))
  threshold_alt0 = relationship("ThresholdAlt0", back_populates="device")
  threshold_alt1 = relationship("ThresholdAlt1", back_populates="device")
  threshold_alt2 = relationship("ThresholdAlt2", back_populates="device")
  threshold_alt3 = relationship("ThresholdAlt3", back_populates="device")
  threshold_alt4 = relationship("ThresholdAlt4", back_populates="device")
  threshold_alt5 = relationship("ThresholdAlt5", back_populates="device")
  threshold_alt6 = relationship("ThresholdAlt6", back_populates="device")
  threshold_alt7 = relationship("ThresholdAlt7", back_populates="device")

  threshold_lc1_id = Column(Integer, ForeignKey('thresholds_lc1.id'))
  threshold_lc1 = relationship("ThresholdLc1", back_populates="device")

  threshold_idl_id = Column(Integer, ForeignKey('thresholds_idl.id'))
  threshold_idl = relationship("ThresholdIdl", back_populates="device")

  bypasses = relationship("Bypass")
