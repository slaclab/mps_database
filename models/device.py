from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship, backref
from models import Base

class Device(Base):
  """
  Device class (devices table)

  This is a generic class that contains properties common to DigitalDevices
  and AnalogDevices.

  Properties:
    name: unique device name (possibly MAD device name)
    description: some extra information about this device
    position: 100 to 999 number that defines approximatelly where the device
              is within the area. This field is used to create PVs
    z_location: z location in ft along the linac
    area: sector where the device is installed (e.g. GUNB, LI30, DMPB,...), this
          is used to create the PVs (second field). This field is used
          to create PVs.
    evaluation: define if device state is evaluated by fast(1) or slow(0) logic.
                default value is slow(0)
    measured_device_type_id: reference to the device_type where this device is located.
                             For example, the sensor type is TEMP, but it is connected
                             to a SOLN. This information is used to generate the proper
                             PV name (e.g. SOLN:<area>:<position>:TEMP)

  References:
    card_id: application card that owns this device

  The discriminator field is used to define whether the device is digital (digital_device)
  or analog (analog_device)

  """
  __tablename__ = 'devices'
  id = Column(Integer, primary_key=True)
  discriminator = Column('type', String(50))
  name = Column(String, unique=True, nullable=False)
  description = Column(String, nullable=False)
  position = Column(Integer, nullable=False)
  z_location = Column(Float, nullable=False, default=0)
  area = Column(String, nullable=False)
  evaluation = Column(Integer, nullable=False, default=0)
#  drawing = Column(String, unique=False, nullable=True)
  card_id = Column(Integer, ForeignKey('application_cards.id'))
  device_type_id = Column(Integer, ForeignKey('device_types.id'), nullable=False)
  measured_device_type_id = Column(Integer, ForeignKey('device_types.id'))
  fault_outputs = relationship("FaultInput", backref='device')
  __mapper_args__ = {'polymorphic_on': discriminator}

  def is_digital(self):
    if self.discriminator == 'digital_device':
      return True
    else:
      return False

  def is_analog(self):
    if self.discriminator == 'analog_device':
      return True
    else:
      return False

class MitigationDevice(Device):
  """
  MitigationDevice class (mitigation_devices table)

  Properties:
    name: mitigation device name (e.g. AOM)
    description:
    
  References:
    beam_destination_id: beam destination for this mitigation device
    channel_id: digital_out_channel connected to the mitigation device
  """
  __tablename__ = 'mitigation_devices'
  __mapper_args__ = {'polymorphic_identity': 'mitigation_device'}
  id = Column(Integer, ForeignKey('devices.id'), primary_key=True)
  beam_destination_id = Column(Integer, ForeignKey('beam_destinations.id'), nullable=False)
  digital_out_channel_id = Column(Integer, ForeignKey('digital_out_channels.id'), nullable=False)

class DigitalDevice(Device):  
  """
  DigitalDevice class (digital_devices table)

  Relationships:
   inputs: list of DeviceInput that use this DigitalDevice
   fault_outputs: list of FaultInputs that use this DigitalDevice as input
  """
  __tablename__ = 'digital_devices'
  __mapper_args__ = {'polymorphic_identity': 'digital_device'}
  id = Column(Integer, ForeignKey('devices.id'), primary_key=True)
  inputs = relationship("DeviceInput", backref='digital_device')
#  fault_outputs = relationship("FaultInput", backref='device')

class AnalogDevice(Device):
  """
  AnalogDevice class (analog_devices table)

  References:
    channel_id: reference to the AnalogChannel that is connected to
                to the actual device

  Relationships:
    threshold_faults: list of ThresholdFaults that reference
                      this AnalogDevice
  """
  __tablename__ = 'analog_devices'
  __mapper_args__ = {'polymorphic_identity': 'analog_device'}
  id = Column(Integer, ForeignKey('devices.id'), primary_key=True)
#  analog_device_type_id = Column(Integer, ForeignKey('analog_device_types.id'), nullable=False)
  channel_id = Column(Integer, ForeignKey('analog_channels.id'), nullable=False, unique=True)
  ignore_conditions = relationship("IgnoreCondition", backref='analog_device')
#  threshold_faults = relationship("ThresholdFault", backref='analog_device')
