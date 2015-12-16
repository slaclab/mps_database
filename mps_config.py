import models
import contextlib
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker

class MPSConfig:
  def __init__(self, filename='mps_config.db'):
    self.engine = create_engine("sqlite:///{filename}".format(filename=filename))
    self.Session = sessionmaker(bind=self.engine)
    self.session = self.Session()
  
  def clear_all(self):
    print("Clearing database...")
    meta = models.Base.metadata
    meta.bind = self.engine
    meta.drop_all()
    meta.create_all()