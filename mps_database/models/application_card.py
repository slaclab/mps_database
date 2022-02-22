from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship, backref, validates
from mps_database.models import Base

class ApplicationCard(Base):
  """
  ApplicationCard class (application_cards table)

  Defines an application card, by specifying its type and location (which 
  crate and slot).

  Properties:
   number: serial/property numbe
   area: sector where the card is installed (e.g. GUNB, LI30, DMPB,...).
             This is used for creating the LinkNode PVs (second field)
   location: this is the location field to generate LinkNode PVs (third field)
   slot_number: number of slot within the ATCA crate where it is installed
   amc: defines whether this card is a carrier (0), an AMC (1) card or RTM (2)
   
  References:
   crate_id: specifies the crate that contains this card
   type_id: specifies the type of this card (e.g. Mixed Mode Link Node type)

  Relationships:
   digital_channels: there are zero or more entries in the
                     digital_channels table pointing to an application_card
                     entry.
   digital_out_channels: 
   analog_channels: there are zero or more entries in the
                    digital_channels table pointing to an application_card
                    entry.
   devices:
   link_node:
  """
  __tablename__ = 'application_cards'
  id = Column(Integer, primary_key=True)
  number = Column(Integer, nullable=False)
  area = Column(String, nullable=False)
  location = Column(String, nullable=False, unique=False)
  slot_number = Column(Integer, nullable=False)
  amc = Column(Integer, nullable=False, default=0)
  crate_id = Column(Integer, ForeignKey('crates.id'), nullable=False)
  type_id = Column(Integer, ForeignKey('application_card_types.id'), nullable=False)
  digital_channels = relationship("DigitalChannel", order_by="asc(DigitalChannel.number)", backref='card')
  digital_out_channels = relationship("DigitalOutChannel", backref='card')
  analog_channels = relationship("AnalogChannel",order_by="AnalogChannel.number", backref='card')
  global_id = Column(Integer, nullable=False, unique=True)
  name = Column(String, unique=False, nullable=False)
  description = Column(String, nullable=True)
  devices = relationship("Device", backref='card')
  link_node_id = Column(Integer, ForeignKey('link_nodes.id'), nullable=False)

  def show(self):
    print(('> Name: {0}'.format(self.name)))
    print(('> Number: {0}'.format(self.number)))
    print(('> Digital: {0}'.format(len(self.digital_channels))))
    print(('> Analog: {0}'.format(len(self.analog_channels))))
    print(('> Digital Out: {0}'.format(len(self.digital_out_channels))))

  def has_virtual_channels(self):
    """
    If there are channels defined between 32 and 47 this card has virtual
    channels. Channels 0 through 31 are for hardwired inputs, while from 32
    to 47 are software settable inputs.
    """
    for c in self.digital_channels:
      if (c.is_virtual()):
        return True

    return False

  @validates('digital_channels')
  def validate_digital_channel(self, key, new_channel):
    """
    When a digital_channel is added to the card, make sure the number
    of digital channels as specified in the application_card_type table
    is not exceeded.
    """
    channel_list = self.digital_channels
    channel_count = self.type.digital_channel_count
    return self.validate_generic_channel(new_channel, channel_list, channel_count)
    
  @validates('analog_channels')
  def validate_analog_channel(self, key, new_channel):
    """
    When a digital_channel is added to the card, make sure the number
    of analog channels as specified in the application_card_type table
    is not exceeded.
    """
    channel_count = self.type.analog_channel_count
    channel_list = self.analog_channels

    return self.validate_generic_channel(new_channel, channel_list, channel_count)
   
  def validate_generic_channel(self, new_channel, channel_list, channel_count):
    """
    Invoked by the digital_channel and analog_channel validators.
    """
    if self.type and len(channel_list)+1 > channel_count:
      raise ValueError("Number of channels on this card cannot exceed the card type's channel count ({count})".format(count=channel_count))
    
    if self.type and new_channel.number >= channel_count:
      raise ValueError("For this card's type, channel number must be < {count}".format(count=channel_count))
    
    if new_channel.number < 0:
      raise ValueError("Channel number must be positive.")
    
    #Ensure the channel isn't taken
    if new_channel.number in [c.number for c in channel_list]:
      raise ValueError("Channel number {num} is already taken by an existing channel ({name}).".format(num=new_channel.number, name=new_channel.name))

    return new_channel
  
  @validates('slot_number')
  def validate_slot_number(self, key, new_slot):
    if self.crate and new_slot > self.crate.num_slots:
      raise ValueError("Slot number must be <= the number of slots in the crate ({count})".format(count=self.crate.num_slots))

    if self.crate and new_slot in [c.slot_number for c in self.crate.cards]: 
        raise ValueError("This slot is already taken by another card in the crate.")

    return new_slot

  def get_card_id(self):
    """
    Return the card ID based on the application
    slot number and application type id.
    
    If the application is a Link Nodes (slot # 2) then
    the card number will be 1

    For other applications, the card number will be
    the slot number + 1.
    """
    if self.slot_number == 2:
      return 1
    else:
      return self.slot_number

  def get_pv_name(self):
    return 'MPLN:{}:{}:{}'.format(self.link_node.area, self.link_node.location, self.get_card_id())
  def get_app_description(self):
    return self.description
