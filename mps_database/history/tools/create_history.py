from mps_database import mps_config, models
from mps_database.history.models import analog_device, bypass_state, device_input, fault_state, mitigation_type
from mps_database.models import Base

from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship, backref



def main():
    tables = [analog_device.AnalogDevice.__table__, bypass_state.BypassState.__table__, fault_state.FaultState.__table__, device_input.DeviceInput.__table__, mitigation_type.MitigationType.__table__]
    #delete_history_db(tables)
    create_history_db(tables)
    return


def create_history_db(tables):
    config_engine = mps_config.MPSConfig(db_file="mps_gun_history.db", db_name="config").last_engine
    Base.metadata.create_all(config_engine, tables=tables)
    #build_fault_table("test").__table__.create(bind = config_engine.last_engine)
    return

def delete_history_db(tables):
    #Add function to delete all tables/rows
    meta = models.Base.metadata
    meta.bind = mps_config.MPSConfig(db_file="mps_gun_history.db", db_name="config").last_engine
    meta.drop_all(tables=tables)
    return

if __name__ == "__main__":
    main()


