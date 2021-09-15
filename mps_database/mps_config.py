
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
  def __init__(self, config_file_name='mps_gun_config.db', runtime_file_name='mps_gun_runtime.db', history_file_name='mps_gun_history.db', db_name=None, db_file=None, file_path=None, debug=False):
    self.db_name = db_name
    self.last_engine = None
    
    current_dbs = ["config", "runtime", "history"]

    #TODO: create real file path defaults - defaults file?
    DEV_RUNTIME_PATH = "/u1/lcls/physics/mps_manager"
    DEV_HISTORY_PATH = "/u1/lcls/physics/mps_history"
    DEV_CONFIG_PATH = "$PHYSICS_TOP/mps_configuration/current"
    lcls_dev = False

    
    # One specific connection is requested
    if self.db_name is not None:
      if self.db_name.lower() in current_dbs:
        # If no filename provided, use default config
        if not db_file:
            db_file = config_file_name
        print("creating a db session with file, path:", db_file, file_path)
        self.create_db_session(db_file, debug, file_path=file_path)
        return

    if lcls_dev:
      # Create all sessions
      self.session = self.create_db_session(config_file_name, debug, file_path=DEV_CONFIG_PATH)
      self.runtime_session = self.create_db_session(runtime_file_name, debug, file_path=DEV_RUNTIME_PATH)
      self.history_session = self.create_db_session(history_file_name, debug, file_path=DEV_HISTORY_PATH)
    else:
      # Create all sessions
      self.session = self.create_db_session(config_file_name, debug)
      self.runtime_session = self.create_db_session(runtime_file_name, debug)
      self.history_session = self.create_db_session(history_file_name, debug)

  def create_db_session(self, filename, debug, file_path=None):
    # Make a path to the directory MPSConfig is in, assume db is in there as well
    if not file_path:
      file_path = os.path.join(os.path.dirname(__file__), filename)
    if filename not in file_path:
      file_path = os.path.join(file_path, filename)
    print("DB File Path: ", file_path)
    engine = create_engine("sqlite:///{path_to_filename}".format(path_to_filename=file_path), echo=debug)
    self.last_engine = engine
    
    Session = sessionmaker(bind=engine)
    self.session = Session()
    return

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
