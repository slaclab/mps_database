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
   location: this is the location field to generate LinkNode PVs (third field, e.g. MP02)
   cpu: name of the LinuxRT CPU where the SIOC is running
   group: MPS update network group number (i.e. CN port the chain connects to)
          group 100 is the CN in LI00, group 200 is the CN in B005
   group_link: index within the group
   group_link_destination: specifies to which LN or CN the link node connects to
   group_drawing: SEDA drawing number showing the nodes in the group
   ln_type: 1=LCLS-I link node, 2=LCLS-II link node, 3=both (for link nodes connected
            to devices that see beam from both injectors)
   lcls1_id: link node id for LCLS-I. This is used to build the link node IP address,
             it goes into the NodeID register.
   slot_number: link nodes connect to only one slots, usually slot 2.
                In some instances they need to connect to cards in other slots.
   
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
  lcls1_id = Column(Integer, nullable=False, default=0)
  slot_number = Column(Integer, nullable=False, default=2)
  crate_id = Column(Integer, ForeignKey('crates.id'))
  cards = relationship("ApplicationCard", backref='link_node')

  def show(self):
    print('> Area: {0}'.format(self.area))
    print('> Location: {0}'.format(self.location))
    print('> CPU: {0}'.format(self.cpu))
    print('> Crate: {0}'.format(self.crate.get_name()))
    print('> Group: {0}'.format(self.group))
    print('> GroupLink: {0}'.format(self.group_link))
    print('> GroupLinkDestination: {0}'.format(self.group_link_destination))
    print('> GroupDrawing: {0}'.format(self.group_drawing))
    print('> LinkNodeType: {}'.format(self.get_ln_type()))
    if (self.ln_type == 1 or self.ln_type == 3):
      print('> LinkNodeType: {}'.format(self.get_type()))
      print('> LinkNodeId: {}'.format(self.lcls1_id))

  def get_ln_type(self):
    if (self.ln_type == 1):
      return 'LCLS-I only'
    elif (self.ln_type == 2):
      return 'LCLS-II only'
    elif (self.ln_type == 3):
      return 'LCLS-I and LCLS-II'
    else:
      return 'Invalid type {}'.format(self.ln_type)

  def get_type(self):
    """
    Return the link node type based on the application cards defined.
    If link node has digital inputs only its type is 'Digital'
    Only analog inputs -> 'Analog'
    Both types of inputs -> 'Mixed'
    """
    has_digital = False
    has_analog = False
    is_slot2 = False
    for c in self.cards:
      if c.slot_number == 2:
        is_slot2 = True
        if c.type.name == 'Digital Card':
          has_digital = True
        elif c.type.name == 'Generic ADC':
          has_analog = True

    if not is_slot2:
      for c in self.cards:
        if c.slot_number == 2:
          is_slot2 = True
          if c.type.name == 'Digital Card':
            has_digital = True
          elif c.type.name == 'Generic ADC':
            has_analog = True

    if has_digital and has_analog:
      return 'Mixed'
    elif has_digital:
      return 'Digital'
    elif has_analog:
      return 'Analog'
    else:
      return 'Analog'

  def get_name(self):
    return 'sioc-' + self.area.lower() + '-' + self.location.lower()

  def get_pv_base(self):
    return 'MPLN:' + self.area.upper() + ':' + self.location.upper()
