from sqlalchemy import Column, Integer, Float, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship, backref
from mps_database.models import Base

class ThresholdFault(Base):
  """
  ThresholdFault class (threshold_faults table)

  Describe an analog fault, which is generated by an AnalogDevice.
  The AnalogDevice provides a compressed analog value from the device,
  the compressed value is expressed a reduced number of bits (e.g. 12).
  The value read from the device is compared to the threshold stored
  here. The conversion from the threshold to analog value is done 
  via the threshold_values_map and threshold_values tables.

  Properties:
    name: short fault description
    greater_than: if true, if the AnalogDevice value is larger than the 
                  compressed_threshold then a ThresholdFault is generated
                  if false, if the AnalogDevice value is smaller than the
                  compressed threshold then a ThresholdFault is generated

  References:
    analog_device_id: defines the type of analog device related to this 
                      fault
    threshold_value_id: defines which threshold value is used when calculating
                        if a fault happened

  Relationships:
    threshold_fault_state: through the ThresholdFaultStates this
    ThresholdFault is linked to an AllowedClass (allowed beam class)
  """
  __tablename__ = 'threshold_faults'
  id = Column(Integer, primary_key=True)
  name = Column(String, nullable=False)
  analog_device_id = Column(Integer, ForeignKey('analog_devices.id'), nullable=False)
  #If greater_than is true, a value larger than the threshold will generate a fault.
  #If greater_than is false, a value smaller than the threshold will generate a fault.
  greater_than = Column(Boolean, nullable=False)
  threshold_fault_state = relationship("ThresholdFaultState", uselist=False, backref="threshold_fault")
  threshold_value_id = Column(Integer, ForeignKey('threshold_values.id'), nullable=False)

  @property
  def less_than(self):
    return not self.greater_than
