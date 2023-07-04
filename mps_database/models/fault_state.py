from sqlalchemy import Table,Column, Integer, String, Boolean, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import relationship, backref, object_session
from mps_database.models import Base
from .beam_class import BeamClass

association_table = Table('association_mitigations',Base.metadata,
                          Column('id',Integer,primary_key=True),
                          Column('fault_state_id',ForeignKey('fault_states.id')),
                          Column('mitigation_id',ForeignKey('mitigations.id')),
                          )

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
    name: Fault state name, used to build GUI states
    value: The value a state should be in to have this state

  Relationships:
    allowed_classes: list of beam allowed classes for this fault
    ignore_conditions: list the ignore conditions that reference this fault_state. When
                       ignore contition is true (e.g. Profile monitor is inserted), then
                       this fault_state is ignored. The only know case so far (Jan 2019)
                       is the insertion of YAG01B screen causing the IM01B/BPM2B charge
                       comparison to be ignored while keeping the IM01B charge threshold
                       active.

  References:
    fault_id: reference to the fault set by this fault_state.
    device_state_id: reference to the device_state that describes in which state the device
                     must be in order to generate the fault.
    beam_destination_id: beam destination for this allowed beam class
    beam_class_id: the BeamClass allowed

  """
  __tablename__ = 'fault_states'
#  __table_args__ = tuple(UniqueConstraint('fault_id', 'device_state_id', sqlite_on_conflict='IGNORE'))
  id = Column(Integer, primary_key=True)
  default = Column(Boolean, nullable=False, default=False)
  name = Column(String, nullable=False)
  value = Column(Integer, nullable=False)
  mask = Column(Integer, nullable=False)
  fault_id = Column(Integer, ForeignKey('faults.id'), nullable=False)
  fault = relationship("Fault",back_populates='fault_states')
  mitigations = relationship("Mitigation",secondary=association_table,back_populates="fault_states")

class Mitigation(Base):
  """
  AllowedClass class (allowed_classes table)

  List of AllowedClasses for a given Fault (via fault_state_id)

  References:
    fault_state_id: the FaultState (Digital or Analog) for this AllowedClass
    beam_destination_id: beam destination for this allowed beam class
    beam_class_id: the BeamClass allowed
  """
  __tablename__ = 'mitigations'
  id = Column(Integer, primary_key=True)
  fault_states = relationship("FaultState",secondary=association_table, back_populates='mitigations')
  beam_destination_id = Column(Integer,ForeignKey('beam_destinations.id'), nullable=False)
  beam_destination = relationship("BeamDestination",back_populates="mitigations")
  beam_class_id = Column(Integer,ForeignKey('beam_classes.id'), nullable=False)
  beam_class = relationship("BeamClass",back_populates="mitigations")