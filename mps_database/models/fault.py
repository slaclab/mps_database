from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean,Table
from sqlalchemy.orm import relationship, backref
from mps_database.models import Base

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
    name: Fault name (e.g. STATE), used in Fault PV name
    description: Text that ends up in the documentation and GUI


  """
  __tablename__ = 'faults'
  id = Column(Integer, primary_key=True)
  pv = Column(String, nullable=False)
  name = Column(String,unique=True, nullable=False)
  fault_inputs = relationship("FaultInput", back_populates='fault')
  fault_states = relationship("FaultState",back_populates='fault')
  ignore_conditions = relationship("IgnoreCondition",secondary=association_ignore,back_populates='faults')


class IgnoreCondition(Base):
  """
  Condition class (conditions table)

  Describe a condition that is composed of current values of one or more 
  digital and/or analog device faults (via FaultStates). Each fault input 
  is represented by a bit (starting at zero). When the combined state of
  the input faults match the condition value it becomes valid.

  A condition is used to ignore one ore more faults (digital and/or analog)

  Properties:
    name: condition identifier (PV attribute)
    description: short description (text in the gui and the document)
    value: bit mask used to verify if condition is met or not. 

  Relationships:
    ignore_conditions: list of fault states that compose this condition
    condition_inputs: list of fault states that are ignored when condition is true
  """
  __tablename__ = 'ignore_conditions'
  id = Column(Integer, primary_key=True)
  name = Column(String, unique=True, nullable=False)
  description = Column(String, nullable=False)
  value = Column(Integer, nullable=False)
  faults = relationship("Fault",secondary=association_ignore, back_populates='ignore_conditions')
  digital_channel_id = Column(Integer, ForeignKey('digital_channels.id'), nullable=False)
  digital_channel = relationship("DigitalChannel",back_populates="ignore_condition")
