
from mps_database import models
from mps_database import runtime 
import contextlib
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker

class MPSConfig:
  #def __init__(self, filename='mps_gun_config.db', runtime_file_name='mps_gun_runtime.db', debug=False):
  def __init__(self, filename='mps_gun_config.db', debug=False):
    self.engine = create_engine("sqlite:///{filename}".format(filename=filename), echo=debug)
    self.Session = sessionmaker(bind=self.engine)
    self.session = self.Session()
 
  def clear_all(self):
    print("Clearing database...")
    meta = models.Base.metadata
    meta.bind = self.engine
    meta.drop_all()
    meta.create_all()

  def find_device_type(self,session,typ,analog=False):
    if analog:
      num = 1
      if typ in ['BPMS']:
        num = 3
    else:
      num = 0    
    dt = session.query(models.DeviceType).filter(models.DeviceType.name == typ).all()
    if len(dt) > 0:
      return dt[0]
    else:
      added_type = models.DeviceType(name=typ,
                                     description=typ,
                                     num_integrators=num)
      session.add(added_type)
      return added_type

  def find_app_card(self,session,card):
    c = session.query(models.ApplicationCard).filter(models.ApplicationCard.number == card).all()
    if len(c) < 1:
      print("ERROR: Cannot find application card ${0}".format(card))
      return
    if len(c) > 1:
      print("ERROR: Fount too many application cards with Global ID ${0}".format(card))
      return
    return c[0]   
