from mps_database import models
from mps_database import runtime 
import contextlib, os
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker

class MPSConfig:
  """
  Responsible for creating and maintaining SQLAlchemy database session objects for
  all mps databases. 
  
  TODO: why are the filenames and file_names not consistent

  Properties:
  References:
  """
  def __init__(self, config_file_name='mps_gun_config.db', runtime_file_name='mps_gun_runtime.db', history_file_name='mps_gun_history.db', db_name=None, db_file=None, debug=False):
    self.db_name = db_name
    current_dbs = ["config", "runtime", "history"]
    
    # One specific connection is requested
    if self.db_name is not None:
      if self.db_name.lower() in current_dbs:
        # If no filename provided, use default config
        if not db_file:
            db_file = config_file_name
        self.session = self.create_db_session(db_file, debug)
        return
    # Create all sessions
    self.session = self.create_db_session(config_file_name, debug)
    self.runtime_session = self.create_db_session(runtime_file_name, debug)
    self.history_session = self.create_db_session(history_file_name, debug)

    """
    self.engine = create_engine("sqlite:///{filename}".format(filename=filename), echo=debug)
    self.Session = sessionmaker(bind=self.engine)
    self.session = self.Session()
    #TODO: the way these sessions work defeat the point of a session maker. Can call this session creator anywhere and they can act as one time sessions
  
    self.runtime_engine = create_engine("sqlite:///{filename}".format(filename=runtime_file_name), echo=debug)
    self.Runtime_Session = sessionmaker(bind=self.runtime_engine)
    self.runtime_session = self.Runtime_Session()

    self.history_engine = create_engine("sqlite:///{filename}".format(filename=history_file_name), echo=debug)
    self.History_Session = sessionmaker(bind=self.history_engine)
    self.history_session = self.History_Session()
    """

  def create_db_session(self, filename, debug):
    # Make a path to the directory MPSConfig is in
    db_path = os.path.join(os.path.dirname(__file__), filename)

    engine = create_engine("sqlite:///{path_to_filename}".format(path_to_filename=db_path), echo=debug)
    new_sessionmaker = sessionmaker(bind=engine)
    return new_sessionmaker

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
