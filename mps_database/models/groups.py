from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship, backref, validates
from mps_database.models import Base

class LinkNodeGroup(Base):
  """
  LinkNodeGroup class (link_nodes table)

  Defines a Link Node (SIOC), which has a one-to-one mapping with crates. 
  Every crate has one LN. The LN also contains information about all
  the application cards configured within the crate.

  Properties:
   number: group number
   
  References:
   link_nodes: specifies the crate that contains this link node
  """
  __tablename__ = 'link_node_groups'
  id = Column(Integer, primary_key=True)
  number = Column(Integer, nullable=False)
  link_nodes = relationship("LinkNode", order_by="LinkNode.lcls1_id", backref='link_node_groups')
  central_node1 = Column(String,nullable=False)
  central_node2 = Column(String,nullable=False)
