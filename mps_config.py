import models
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

class MPSConfig:
  def __init__(self):
    self.engine = create_engine('sqlite:///mps_config.db')
    Session = sessionmaker(bind=self.engine)
    self.session = Session()