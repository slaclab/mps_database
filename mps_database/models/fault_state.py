from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, backref
from mps_database.models import Base
from .allowed_class import AllowedClass

class FaultState(Base):
  """
  FaultState class (fault_states table)

  A FaultState defines which states of a device generate a fault, which in turn causes
  a change in the allowed beam class at different destinations.

  For example a profile monitor target screen has four states: IN, OUT, BROKEN or MOVING.
  These are the DeviceStates defined for that type of device. The OUT state is active
  when the target screen is out of the beam trajectory path, not requiring any action
  by the MPS system. When its state changes either to MOVING or BROKEN then actual
  position of the screen is unknown, thus MPS must turn off the beam in order to prevent
  the electron bunches from hitting the screen holder or damaging the screen if the
  beam power is higher that supported. For the IN status MPS must assert a beam class
  that is safe for the screen (e.g. 10Hz at 100pC).

  The FaultState does not distinguish between analog vs digital devices, it only knows
  about DeviceStates, which are used for both types of devices.

  Properties:
    default: defines if this state is the default for the fault, i.e. if other digital
             states are not faulted, it defaults to this one

  Relationships:
    allowed_classes: list of beam allowed classes for this fault
    ignore_conditions: list the ignore conditions that reference this fault_state. When
                       ignore contition is true (e.g. Profile monitor is inserted), then
                       this fault_state is ignored. The only know case so far (Jan 2019)
                       is the insertion of YAG01B screen causing the IM01B/BPM2B charge
                       comparison to be ignored while keeping the IM01B charge threshold
                       active.
    contition_inputs: this fault_state is used as input to conditions, e.g. the IN state
                      of profile monitor screens are used as condition_inpus to ignore
                      faults from downstream devices (e.g. BPMs).

  References:
    fault_id: reference to the fault set by this fault_state.
    device_state_id: reference to the device_state that describes in which state the device
                     must be in order to generate the fault.

  """
  __tablename__ = 'fault_states'
#  __table_args__ = tuple(UniqueConstraint('fault_id', 'device_state_id', sqlite_on_conflict='IGNORE'))
  id = Column(Integer, primary_key=True)
  allowed_classes = relationship("AllowedClass", backref='fault_state')
  ignore_conditions = relationship("IgnoreCondition", backref='fault_state')
  condition_inputs = relationship("ConditionInput", backref='fault_state')
  default = Column(Boolean, nullable=False, default=False)
  fault_id = Column(Integer, ForeignKey('faults.id'), nullable=False)
  device_state_id = Column(Integer, ForeignKey('device_states.id'), nullable=False)
  

  def add_allowed_class(self, beam_class, beam_destination):
    ac = AllowedClass()
    ac.beam_class = beam_class
    ac.beam_destination = beam_destination
    self.allowed_classes.append(ac)
    return ac
  
  def add_allowed_classes(self, beam_classes, beam_destination):
    acs = []
    for c in beam_classes:
      acs.append(self.add_allowed_class(c, beam_destination))
    return acs

