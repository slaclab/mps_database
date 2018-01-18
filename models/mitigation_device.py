from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, backref
from models import Base

class MitigationDevice(Base):
  """
  MitigationDevice class (mitigation_devices table)

  Properties:
    name: mitigation device name (e.g. AOM)
    description:
    
  References:
    beam_destination_id: beam destination for this mitigation device
    channel_id: digital_out_channel connected to the mitigation device
  """
  __tablename__ = 'mitigation_devices'
  id = Column(Integer, primary_key=True)
  name = Column(String, nullable=False, unique=True)
  description = Column(String, nullable=False)
  beam_destination_id = Column(Integer, ForeignKey('beam_destinations.id'), nullable=False)
  digital_out_channel_id = Column(Integer, ForeignKey('digital_out_channels.id'), nullable=False)
