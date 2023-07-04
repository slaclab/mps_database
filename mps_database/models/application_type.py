from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from mps_database.models import Base

class ApplicationType(Base):
  """
  ApplicationType (application_card_types table)

  Describe an application card type that physically takes one slot. An 
  ApplicationCard is an ATCA carrier card with (or without) AMCs.

  It has a defined number of digital and analog channels, as described
  by the DigitalChannel class (digital_channels table) and 
  AnalogChannel class (analog_channels table).

  Properties:
   id: unique application card type identifier
   name: Currently, support 'MPS Analog','BCM','BLEN','Wire Scanner','LLRF','RTM Digital','MPS Digital'
   analog_channel_count: number of analog channels
   digital_channel_count: number of digital channels

  Relationships:
   cards: which ApplicationCards (application_cards table) are of this type
  """
  __tablename__ = 'application_card_types'
  id = Column(Integer, primary_key=True)
  name = Column(String, nullable=False, unique=True)
  num_integrators = Column(Integer,nullable=True)
  analog_channel_count = Column(Integer, nullable=False)
  digital_channel_count = Column(Integer, nullable=False)
  software_channel_count = Column(Integer, nullable=False)
  cards = relationship("ApplicationCard", back_populates='type')

  def get_integrator(self,fault=None):
    integrator = None
    if self.num_integrators > 0:
      if fault == None:
        return 0
      else:
        name = fault.split(':')[-1]
        if name == 'TMIT':
          return 0
        elif name == 'X':
          return 1
        elif name == 'Y':
          return 2
        else:
          return 0