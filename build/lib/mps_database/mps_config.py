from mps_database import models
from mps_database import runtime 
import contextlib, glob
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker

class MPSConfig:
  #def __init__(self, filename='mps_gun_config.db', runtime_file_name='mps_gun_runtime.db', debug=False):
  def __init__(self, filename=None, debug=False,verbose=False):
    if not filename:
      print("Need to specify a filename")
    self.engine = create_engine("sqlite:///{filename}".format(filename=filename), echo=debug)
    self.Session = sessionmaker(bind=self.engine)
    self.session = self.Session()
    self.verbose=verbose
 
  def clear_all(self):
    print("Clearing database...")
    meta = models.Base.metadata
    meta.bind = self.engine
    meta.drop_all()
    meta.create_all()
  

