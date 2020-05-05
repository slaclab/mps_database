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

  def get_bit_position(self):
    integrator = self.get_integrator()
    bit_position = 0
    bit_found = False
    initial_shift = 1 * 8 * integrator
    shift = initial_shift
    #print 'Integrator: {0}, shift: {1}, value: {2}'.format(integrator, shift, self.value)
    while not bit_found:
      b = (self.value >> shift) & 1
      if b == 1:
        return bit_position
      else:
        shift = shift + 1 # move to next bit
        bit_position = bit_position + 1
      #print 'Integrator: {0}, shift: {1}'.format(integrator, shift)

      if (shift >= initial_shift + 8):
        raise ValueError('Cannot find the bit position for value={0}'.format(self.value))
        print 'Cannot find the bit position for value={0}'.format(self.value)
        return 0
