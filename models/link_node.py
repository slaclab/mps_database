from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship, backref, validates
from models import Base

class LinkNode(Base):
  """
  LinkNode class (link_nodes table)

  Defines a Link Node (SIOC), which has a one-to-one mapping with crates. 
  Every crate has one LN. The LN also contains information about all
  the application cards configured within the crate.

  Properties:
   area: sector where the card is installed (e.g. GUNB, LI30, DMPB,...).
             This is used for creating the LinkNode PVs (second field)
   location: this is the location field to generate LinkNode PVs (third field)
   cpu: name of the LinuxRT CPU where the SIOC is running
   
  References:
   crate_id: specifies the crate that contains this link node
  """
  __tablename__ = 'link_nodes'
  id = Column(Integer, primary_key=True)
  area = Column(String, nullable=False)
  location = Column(String, nullable=False, unique=False)
  cpu = Column(String, nullable=False, unique=True)
  crate = relationship("Crate", uselist=False, back_populates="link_node")
#  crate_id = Column(Integer, ForeignKey('crates.id'), nullable=False)
  
  def show(self):
    print('> Area: {0}'.format(self.area))
    print('> Location: {0}'.format(self.location))
    print('> CPU: {0}'.format(self.cpu))
#    print('> CrateId: {0}'.format(self.crate_id))

  def get_name(self):
    return 'sioc-' + self.area + '-' + self.location
