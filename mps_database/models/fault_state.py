from sqlalchemy import Table,Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from mps_database.models import Base

# This association table provides a many-to-many link between fault states and mitigations
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

  Properties:
    default: defines if this state is the default for the fault, i.e. if other digital
             states are not faulted, it defaults to this one
    name: Fault state name, used to build GUI states
    value: The value a state should be in to have this state
    mask: The bitmask for this fault state

  Relationships:
    mitigation: list of beam mitigations for this fault state
    fault: the fault that contains this fault state
  """
  __tablename__ = 'fault_states'
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
  Mitigation

  List of Mitigation for a given Fault (via fault_state)
  Links a fault state to a destination and beam class

  References:
    fault_state: the FaultState (Digital or Analog) for this AllowedClass
    beam_destination: beam destination for this allowed beam class
    beam_class: the BeamClass allowed
  """
  __tablename__ = 'mitigations'
  id = Column(Integer, primary_key=True)
  fault_states = relationship("FaultState",secondary=association_table, back_populates='mitigations')
  beam_destination_id = Column(Integer,ForeignKey('beam_destinations.id'), nullable=False)
  beam_destination = relationship("BeamDestination",back_populates="mitigations")
  beam_class_id = Column(Integer,ForeignKey('beam_classes.id'), nullable=False)
  beam_class = relationship("BeamClass",back_populates="mitigations")