from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship
from mps_database.models import Base

class CentralNode(Base):
  """
  CentralNode class (central_nodes table)

  Defines a Central Node, which has a one-to-many mapping with link node groups. 
  There are currently three central nodes

  Properties:
   area: sector where the central node is installed (e.g. SYS0, SYS1, etc,...).
   location: this is the location field to generate LinkNode PVs (third field, e.g. MP01)
   slot: what slot in the crate is it in
   
  References:
   crate: specifies the crate that contains this central node
   groups: specifies the groups that link to this central node
  """

  __tablename__ = 'central_nodes'
  id = Column(Integer, primary_key=True)
  area = Column(String, nullable=False)
  location = Column(String, nullable=False)
  slot = Column(Integer, nullable=False)
  groups = relationship("LinkNodeGroup",back_populates='central_node')
  crate = relationship("Crate",back_populates='central_nodes')
  crate_id = Column(Integer,ForeignKey("crates.id"))

  def get_full_location(self):
    return '{0}-S{1}'.format(self.crate.get_full_location(),self.slot)

  def get_cn_number(self):
    return self.id

  def get_cn_prefix(self):
    return 'SIOC:{0}:{1}'.format(self.area.upper(),self.location.upper())

