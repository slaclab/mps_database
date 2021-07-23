from mps_database.mps_config import MPSConfig, models
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship, backref



# this probably already exists, see if I can establish a connection to the config db

def connect_db():
    # gun, runtime dbs hardcoded for now
    #TODO: add cli args later
    conf = MPSConfig(db_name="config", db_file='mps_config_imported.db')
    return conf

#TODO: is imported the default name now? Or is that just for testing?

def query_beamclass():
    conf_session = connect_db().session()
    print(conf_session)
    print(conf_session.query(models.BeamClass.name).all())
    return

def add_log():
    return
    

if __name__ == "__main__":
    query_beamclass()