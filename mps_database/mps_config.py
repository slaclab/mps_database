import models
import runtime 
import contextlib
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker

class MPSConfig:
  def __init__(self, filename='mps_gun_config.db', runtime_file_name='mps_gun_runtime.db', debug=False):
    self.engine = create_engine("sqlite:///{filename}".format(filename=filename), echo=debug)
    self.Session = sessionmaker(bind=self.engine)
    self.session = self.Session()
  
    self.runtime_engine = create_engine("sqlite:///{filename}".format(filename=runtime_file_name), echo=debug)
    self.Runtime_Session = sessionmaker(bind=self.runtime_engine)
    self.runtime_session = self.Runtime_Session()

  def clear_all(self):
    print("Clearing database...")
    meta = models.Base.metadata
    meta.bind = self.engine
    meta.drop_all()
    meta.create_all()

    meta = runtime.RuntimeBase.metadata
    meta.bind = self.runtime_engine
    meta.drop_all()
    meta.create_all()
