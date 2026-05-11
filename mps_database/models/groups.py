from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship
from mps_database.models import Base
from sqlalchemy.orm import object_session
from .link_node import LinkNode
from .crate import Crate
from collections import Counter

class LinkNodeGroup(Base):
  """
  LinkNodeGroup class (link_node_groups table)

  Defines a Link Node group which contains a collection of link nodes for
  data transmission

  Properties:
   number: group number
   
  References:
   link_nodes: specifies the crate that contains this link node
   central_node_id: Which central node does this group connect to
  """
  __tablename__ = 'link_node_groups'
  id = Column(Integer, primary_key=True)
  number = Column(Integer, nullable=False)
  link_nodes = relationship("LinkNode",order_by="LinkNode.lnid", back_populates='group')
  central_node_id = Column(Integer,ForeignKey('central_nodes.id'), nullable=False)
  central_node = relationship("CentralNode",back_populates="groups")

  def get_central_node(self):
    return self.central_node

  def find_last_ln(self):
    found_central_nodes = []
    for ln in self.link_nodes:
      cr = ln.get_group_link()
      if cr.has_cn():
        found_central_nodes.append(ln)
    if len(found_central_nodes) < 1 or len(found_central_nodes) > 1:
      print("ERROR: Expected to find 1 central node, found {0}".format(len(found_central_nodes)))
      return None
    else:
      last_ln = found_central_nodes[0]
      return last_ln

  def find_first_lns(self):
    first_lns = []
    max_len = 0
    session = object_session(self)
    for ln in self.link_nodes:
      location = ln.crate.location
      in_lns = session.query(LinkNode).filter(LinkNode.group_link==location).all()
      if len(in_lns) == 0:
        chain = self.build_ln_chain(ln)
        if chain['length'] > max_len:
          first_lns.append(ln)
        else:
          first_lns.insert(0,ln)
    return first_lns

  def find_split_lns(self):
    split_lns = []
    session = object_session(self)
    for ln in self.link_nodes:
      location = ln.crate.location
      in_lns = session.query(LinkNode).filter(LinkNode.group_link==location).all()
      if len(in_lns) > 1:
        split_lns.append(ln)
    return split_lns

  def find_next_ln(self,ln):
    session = object_session(self)
    location = ln.group_link
    next_crate = session.query(Crate).filter(Crate.location==location).one()
    if next_crate.has_ln():
      next_ln = next_crate.link_node[0]
    else:
      next_ln = None
    return next_ln


  def build_ln_chain(self,first_ln):
    count = 1
    split_lns = self.find_split_lns()
    split_ln_locations = []
    for split_ln in split_lns:
      split_ln_locations.append(split_ln.crate.location)
    last_ln = self.find_last_ln()
    chain = {}
    key = "{0}".format(count)
    chain[key] = first_ln
    keep_going = True
    previous_ln = first_ln
    while(keep_going):
      ln = self.find_next_ln(previous_ln)
      if ln == None:
        keep_going = False
        continue
      count = count + 1
      key = "{0}".format(count)
      chain[key] = ln
      previous_ln = ln
      if ln.crate.location == last_ln.crate.location:
        keep_going = False
    chain['length'] = count
    return(chain)

    
      

