from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship
from sqlalchemy.orm import object_session
from .crate import Crate
import ipaddress
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
   crate: specifies the crate that contains this link node
   group: specifies the group this link node is a member of
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
    return 'MPLN:{0}:{1}'.format(self.crate.area.upper(),self.location.upper())

  def get_app_cards(self):
    return self.crate.cards

  def get_app_card(self,slot):
    card = None
    for c in self.get_app_cards():
      if c.slot == slot:
        card = c
    return card

  def get_group_link(self):
    session = object_session(self)
    linked_crate = session.query(Crate).filter(Crate.location==self.group_link).all()
    if len(linked_crate) > 1:
      print("ERROR: Too many linked crates in LN{0}".format(self.lnid))
      return None
    if len(linked_crate) < 1:
      print("ERROR: Not enough linked crates in LN{0}".format(self.lnid))
      return None
    if len(linked_crate) == 1:
      return linked_crate[0]

  def get_out_path(self):
    return '{}/{:04}/{:02}'.format(self.crate.get_cpu_nodename(),self.crate.crate_id,2)

  def get_salt(self):
    return '0x3e'

  def get_digital_app_id(self):
    for card in self.get_app_cards():
      if card.slot < 3:
        if card.is_mps_digital():
          return card.number
    return 0

  def map_nc_config(self):
    """
    Return dictionary of macros to be written to yaml config file
    """
    if self.lnid == "0":
      ip_str = '0.0.168.192'.format(app["app_id"])
      print('ERROR: Found invalid link node ID (lnid of 0)')
    else:
      ip_str = '{}.0.168.192'.format(self.lnid)
    ip_address = int(ipaddress.ip_address(ip_str))
    mask = 0
    remap_dig = self.get_digital_app_id()
    if remap_dig > 0:
      mask = 1
    bpm_index = 0
    blm_index = 0
    remap_bpm = [0, 0, 0, 0, 0]
    remap_blm = [0, 0, 0, 0, 0]
    for card in self.get_app_cards():
      if card.type.name == 'BPM':
        if bpm_index < 5:
          remap_bpm[bpm_index] = card.number
          bpm_index +=1
        else:
          print(('ERROR: Cannot remap BPM app id {}, all remap slots are used already'.\
                format(slot_info["app_id"])))
      elif card.type.name == "MPS Analog":
        if blm_index < 5:
          remap_blm[blm_index] = card.number
          mask |= 1 << (blm_index + 1 + 5) # Skip first bit and 5 BPM bits
          blm_index += 1
        else:
          print(('ERROR: Cannot remap BLM app id {}, all remap slots are used already'.\
                format(slot_info["app_id"])))
    macros={"ID":'{0}'.format(self.lnid),
              "IP_ADDR":str(ip_address),
              "REMAP_DIG":str(remap_dig),
              "REMAP_BPM1":str(remap_bpm[0]),
              "REMAP_BPM2":str(remap_bpm[1]),
              "REMAP_BPM3":str(remap_bpm[2]),
              "REMAP_BPM4":str(remap_bpm[3]),
              "REMAP_BPM5":str(remap_bpm[4]),
              "REMAP_BLM1":str(remap_blm[0]),
              "REMAP_BLM2":str(remap_blm[1]),
              "REMAP_BLM3":str(remap_blm[2]),
              "REMAP_BLM4":str(remap_blm[3]),
              "REMAP_BLM5":str(remap_blm[4]),
              "REMAP_MASK":str(mask),
              }
    return macros

  def get_ln_properties(self):
    """
    Return a dictionary of properties about link node
    """
    macros = {}
    macros["lnid"] = self.lnid
    macros["p"] = self.get_mps_prefix()
    macros["group"] = self.group.number
    macros["cpu"] = self.crate.get_cpu_nodename()
    macros["shm"] = self.crate.get_nodename()
    macros["crate"] = self.crate.location
    macros["sioc"] = self.get_app_card(1).get_ioc_name()
    slots = range(1,8)
    for slot in slots:
      key = "slot{0}".format(slot)
      card = self.get_app_card(slot)
      if card is not None:
        used = 1
        type = card.type.name
        type_short = card.type.get_short_name()
        app = card.number
        app_text = "{0}".format(card.number)
      else:
        used = 0
        type = "---"
        app_text = "---"
        type_short = "NONE"
        app = -1
      slot_prop = {}
      slot_prop['used'] = used
      slot_prop['type'] = type
      slot_prop['short_name'] = type_short
      slot_prop['app'] = app
      slot_prop['app_text'] = app_text
      macros[key] = slot_prop
    return macros
