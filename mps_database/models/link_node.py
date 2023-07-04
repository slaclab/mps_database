from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship, backref, validates
from sqlalchemy.orm import object_session
from .crate import Crate
from mps_database.models import Base

class LinkNode(Base):
  """
  LinkNode class (link_nodes table)

  Defines a Link Node (SIOC), which has a one-to-one mapping with crates. 
  Every crate has one LN. The LN also contains information about all
  the application cards configured within the crate.

  Properties:
   location: this is the location field to generate LinkNode PVs (third field, e.g. MP02)
   group_link: crate this link node connects to
   rx_pgp: pgp port number this crate connect to
   ln_type: 1=LCLS-I link node, 2=LCLS-II link node, 3=both (for link nodes connected
            to devices that see beam from both injectors)
   lnid: link node id. This is used to build the link node IP address,
   
  References:
   crate_id: specifies the crate that contains this link node
   group_id: specifies the group this link node is a member of
  """
  __tablename__ = 'link_nodes'
  id = Column(Integer, primary_key=True)
  location = Column(String, nullable=False, unique=False)
  group_link = Column(String, unique=False)
  rx_pgp = Column(Integer, unique=False)
  ln_type = Column(Integer, nullable=False, default=2)
  lnid = Column(Integer, nullable=False, default=0)
  crate = relationship("Crate", back_populates='link_node')
  crate_id = Column(Integer,ForeignKey("crates.id"),nullable=False)
  group_id = Column(Integer, ForeignKey('link_node_groups.id'), nullable=False)
  group = relationship('LinkNodeGroup',back_populates='link_nodes')

  def get_mps_prefix(self):
    return 'MPLN:{0}:{1}'.format(self.crate.area,self.location)

  def get_app_cards(self):
    return self.crate.cards

  def get_group_link(self):
    session = object_session(self)
    linked_crate = session.query(Crate).filter(Crate.location==self.group_link).all()
    if len(linked_crate) > 1:
      print("ERROR: Too many linked crates in LN{0}".format(self.lnid))
      return Null
    if len(linked_crate) < 0:
      print("ERROR: Not enough linked crates in LN{0}".format(self.lnid))
      return null
    if len(linked_crate) == 1:
      return linked_crate[0]
