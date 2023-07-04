from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from mps_database.models import Base

class Crate(Base):
  """
  Crate class (crates table)
  
  Describes an ATCA crate, properties are:
    crate_id: The first crate attached to a CPU is 1, the second is 101
    num_slots: number of slots available (usually 2 or 7)
    location: Full location of this crate (L2KA00-1532)
    rack: string containing the rack identifier (e.g. 05)
    elevation: elevation within the rack
    area: Control system area where the crate is (e.g. BC1B)
    node: SharedPlatform designator (e.g. SP03)

  Relationships:
    cards: each ApplicationCard has a reference to a crate 

  References:
    link_node: points to the link node (in slot 2) within this crate. 
    central_node: points to the central nodes within this crate. 
  """
  __tablename__ = 'crates'
  id = Column(Integer, primary_key=True)
  crate_id = Column(Integer, nullable=False)
  num_slots = Column(Integer, nullable=False)
  location = Column(String, nullable=False)
  rack = Column(String, nullable=False)
  elevation = Column(Integer, nullable=False, default=0)
  area = Column(String,nullable=False)
  node = Column(String,nullable=False)
  central_nodes = relationship("CentralNode",back_populates='crate')
  cards = relationship("ApplicationCard",order_by="ApplicationCard.slot", back_populates='crate')
  link_node = relationship("LinkNode",back_populates='crate')

  def get_full_location(self):
    return self.location

  def get_nodename(self):
    crate_number = 1
    if self.crate_id == 101:
      crate_number = 2
    return 'shm-{0}-{1}-{2}'.format(self.area.lower(),self.node.lower(),crate_number)

  def get_cpu_nodename(self):
    return 'cpu-{0}-{1}'.format(self.area.lower(),self.node.lower())

  def get_cpu_pvname(self):
    return 'CPU:{0}:{1}'.format(self.area.upper(),self.node.upper())

  def has_ln(self):
    if len(self.link_node) > 0:
      return True
    else:
      return False

  def has_cn(self):
    if len(self.central_nodes) > 0:
      return True
    else:
      return False

  # Link nodes and crates have a one-to-one mapping, but something needed to be 
  # the "parent" object.  Crate is the "parent" and link_node is the "child"
  def get_ln(self):
    return self.link_node[0]
    
    
