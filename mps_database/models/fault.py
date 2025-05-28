from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean,Table,func
from sqlalchemy.orm import relationship, object_session
from mps_database.models import Base
from .beam_class import BeamClass

# This is used to map many-to-many between faults and ignore conditions
association_ignore = Table('association_ignore',Base.metadata,
                          Column('id',Integer,primary_key=True),
                          Column('fault_id',ForeignKey('faults.id')),
                          Column('ignore_condition_id',ForeignKey('ignore_conditions.id')),
                          )

class Fault(Base):
  """
  Fault class (faults table)

  This is a class that contains properties common to faults (truth tables)

  Properties:
    name: Fault name which will be in the gui
    pv: String that will be used to build fault PV (e.g. POSITION)

  Relationships:
    fault_inputs: channels that feed into this fault (truth table)
    fault_states: states this fault can be in depending on fault_inputs
    ignore_condition: Conditions which will cause this fault to be ignored.
  """
  __tablename__ = 'faults'
  id = Column(Integer, primary_key=True)
  pv = Column(String, nullable=False)
  name = Column(String,unique=True, nullable=False)
  fault_inputs = relationship("FaultInput",order_by="FaultInput.bit_position", back_populates='fault')
  fault_states = relationship("FaultState",back_populates='fault')
  ignore_conditions = relationship("IgnoreCondition",secondary=association_ignore,back_populates='faults')

  def skip_shutter(self):
    """
    This function will determine if the mechanical shutter and BSYD mitigations are the same for all states.  
    If they are, the shutter can be skipped in the report
    """
    skip = True
    for s in self.fault_states:
      mits = s.get_beam_classes()
      if mits['MECH_SHUTTER'] != mits['SC_BSYD']:
        skip = False
    return skip

  def skip_laser(self):
    """
    This function will determine if the laser mitigation mitigations is nothing for all states.  
    If they are, the shutter can be skipped in the report
    """
    session = object_session(self)
    max_beam_class = session.query(func.max(BeamClass.number)).one()[0]
    skip = True
    for s in self.fault_states:
      mits = s.get_beam_classes()
      if mits['LASER'] == max_beam_class:
        skip = False
    return skip

  def get_ignore_group(self):
    ignore_group = []
    if len(self.ignore_conditions) > 0:
      for ic in self.ignore_conditions:
        ignore_group.append(ic.description)
    else:
      ignore_group = ['Always Evaluated']
    ignore_group.sort()
    return(ignore_group)


class IgnoreCondition(Base):
  """
  IgnoreCondition class (ignore_conditions table)

  Describe a condition that is composed of current values of one digital channel.
  When that channel is active, the condition will be true and the collection
  of faults will be ignored.

  Properties:
    name: condition identifier (PV attribute)
    description: short description (text in the gui and the document)
    value: bit mask used to verify if condition is met or not. 

  Relationships:
    faults: list of fault that are ignored by this condition
    digital_channel: The channel that when active will cause this condition to be true
  """
  __tablename__ = 'ignore_conditions'
  id = Column(Integer, primary_key=True)
  name = Column(String, unique=True, nullable=False)
  description = Column(String, nullable=False)
  value = Column(Integer, nullable=False)
  central_node = relationship("CentralNode",back_populates='ignore_conditions')
  central_node_id = Column(Integer,ForeignKey('central_nodes.id'),nullable=False)
  faults = relationship("Fault",secondary=association_ignore, back_populates='ignore_conditions')
  digital_channel_id = Column(Integer, ForeignKey('digital_channels.id'), nullable=False)
  digital_channel = relationship("DigitalChannel",back_populates="ignore_condition")
