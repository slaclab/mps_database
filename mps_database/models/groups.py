from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship, backref, validates
from mps_database.models import Base

class LinkNodeGroup(Base):
  """
  LinkNodeGroup class (link_node_groups table)

  Defines a Link Node (SIOC), which has a one-to-one mapping with crates. 
  Every crate has one LN. The LN also contains information about all
  the application cards configured within the crate.

  Properties:
   number: group number
   
  References:
   link_nodes: specifies the crate that contains this link node
   central_node_id: Which central node does this group connect to
  """
  __tablename__ = 'link_node_groups'
  id = Column(Integer, primary_key=True)
  number = Column(Integer, nullable=False)
  link_nodes = relationship("LinkNode", order_by="LinkNode.lnid", back_populates='group')
  central_node_id = Column(Integer,ForeignKey('central_nodes.id'), nullable=False)
  central_node = relationship("CentralNode",back_populates="groups")
