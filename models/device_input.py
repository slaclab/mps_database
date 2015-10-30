from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, backref
from models import Base

class DeviceInput(Base):
  __tablename__ = 'device_inputs'
  id = Column(Integer, primary_key=True)
  device_id = Column(Integer, ForeignKey('devices.id'), nullable=False)
  bit_position = Column(Integer, nullable=False)
  channel_id = Column(Integer, ForeignKey('link_node_channels.id'), nullable=False)