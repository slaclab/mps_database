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
   group: MPS update network group number (i.e. CN port the chain connects to)
          group 100 is the CN in LI00, group 200 is the CN in B005
   group_link: index within the group
   group_link_destination: specifies to which LN or CN the link node connects to
   group_drawing: SEDA drawing number showing the nodes in the group
   ln_type: 1=LCLS-I link node, 2=LCLS-II link node, 3=both (for link nodes connected
            to devices that see beam from both injectors)
   
  References:
   crate_id: specifies the crate that contains this link node
  """
  __tablename__ = 'link_nodes'
  id = Column(Integer, primary_key=True)
  area = Column(String, nullable=False)
  location = Column(String, nullable=False, unique=False)
  cpu = Column(String, nullable=False, unique=False)
  group = Column(Integer, unique=False)
  group_link = Column(Integer, unique=False)
  group_link_destination = Column(Integer, unique=False)
  group_drawing = Column(String, unique=False)
  ln_type = Column(Integer, nullable=False, default=2)
  crate = relationship("Crate", uselist=False, back_populates="link_node")
  
  def show(self):
    print('> Area: {0}'.format(self.area))
    print('> Location: {0}'.format(self.location))
    print('> CPU: {0}'.format(self.cpu))
    print('> Crate: {0}'.format(self.crate.get_name()))
    print('> Group: {0}'.format(self.group))
    print('> GroupLink: {0}'.format(self.group_link))
    print('> GroupLinkDestination: {0}'.format(self.group_link_destination))
    print('> GroupDrawing: {0}'.format(self.group_drawing))

  def get_name(self):
    return 'sioc-' + self.area.lower() + '-' + self.location.lower()
