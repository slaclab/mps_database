from mps_database import mps_config, models
from mps_database.history.models import fault_history, input_history
from mps_database.models import Base

from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship, backref



def main():
    #delete_history_db()
    create_history_db()
    return


def create_history_db():
    tables_to_build = {fault_history.FaultHistory.__table__, input_history.InputHistory.__table__}
    config_engine = mps_config.MPSConfig(db_file="mps_gun_history.db", db_name="config").last_engine
    Base.metadata.create_all(config_engine, tables=tables_to_build)
    #build_fault_table("test").__table__.create(bind = config_engine.last_engine)
    return

def delete_history_db():
    #Add function to delete all tables/rows
    meta = models.Base.metadata
    meta.bind = mps_config.MPSConfig(db_file="mps_gun_history.db", db_name="config").last_engine
    meta.drop_all(tables=[fault_history.FaultHistory.__table__, input_history.InputHistory.__table__])
    return

if __name__ == "__main__":
    main()


