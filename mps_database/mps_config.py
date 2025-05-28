from mps_database import models
import contextlib, glob
from sqlalchemy import create_engine, MetaData, func
from sqlalchemy.orm import sessionmaker, object_session

class MPSConfig:
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
    meta.drop_all(bind=self.engine)
    meta.create_all(bind=self.engine)

  def get_max_bc(self):
    return self.session.query(func.max(models.BeamClass.number)).one()[0]

  

