from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from models import Base
class ApplicationCardType(Base):
  __tablename__ = 'application_card_types'
  id = Column(Integer, primary_key=True)
  number = Column(Integer, nullable=False, unique=True)
  name = Column(String, nullable=False, unique=True)
  channel_count = Column(Integer, nullable=False)
  channel_size = Column(Integer, nullable=False)
  cards = relationship("ApplicationCard", backref='type')