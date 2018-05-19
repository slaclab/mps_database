from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, backref
from models import Base

class DeviceState(Base):
  """
  DeviceState class (device_states table)

  Describe a state of a DigitalDevice, based on its value. 

  Properties:
    name: 
    description: short explanation of the state
    value: the value a Device should have to be in this state
    mask: bit mask used to ignore certain bits from the Device value
          before comparing the DeviceState value

  References:
    device_type_id: reference to the DeviceType that can be in this state

  Relationships:
    
    
  """
  __tablename__ = 'device_states'
  id = Column(Integer, primary_key=True)
  name = Column(String, nullable=False)
  description = Column(String, nullable=True)
  value = Column(Integer, nullable=False)
  mask = Column(Integer, nullable=False, default=0xFFFFFFFF)
  device_type_id = Column(Integer, ForeignKey('device_types.id'), nullable=False)
  fault_states = relationship("FaultState", backref='device_state')

  # This is valid only for AnalogDevice states, where the value
  # contains only one high bit. Based on the value this returns
  # to which integrator it belongs
  def get_integrator(self):
    if self.value < 0x100:
      return 0
    elif self.value < 0x10000:
      return 1
    elif self.value < 0x1000000:
      return 2
    else:
      return 3
