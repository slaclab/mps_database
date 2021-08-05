from mps_database.mps_config import MPSConfig, models
from mps_database.history.models import fault_history, input_history
from sqlalchemy import insert

from sqlalchemy.orm import relationship, backref

"""
class HistorySession():
    def __init__(self):

        return
"""
#use for testing
def main():
    history_class = connect_hist_db()
    print("\n", history_class.session)

    fault_id = 1
    add_fault(history_class, fault_id)
    faults = [22, 23, 24]
    add_faults(history_class, faults)
    return


def connect_hist_db():
    conf = MPSConfig(db_name="history", db_file='mps_gun_history.db')
    return conf

def connect_conf_db():
    # gun, runtime dbs hardcoded for now
    #TODO: add cli args later
    conf = MPSConfig(db_name="config", db_file='mps_config_imported.db')
    return conf

#TODO: is imported the default name now? Or is that just for testing?

def query_beamclass():
    conf_session = connect_conf_db().session()
    print(conf_session)
    print(conf_session.query(models.BeamClass.name).all())
    return

def add_fault(history_conn, fault_id):
    fault_insert = fault_history.FaultHistory.__table__.insert().values(id=fault_id, timestamp='time')
    history_conn.last_engine.execute(fault_insert)
    print("\n", history_conn.session)
    history_conn.session.commit()
    return

def add_faults(history_conn, fault_ids):
    faults_info = []
    for fid in fault_ids:
        faults_info += ({'id': fid, 'timestamp':'time'})
    history_conn.last_engine.execute(fault_history.FaultHistory.__table__.insert(), faults_info)
    history_conn.session.commit()
    return
    
def get_entry():
    return

if __name__ == "__main__":
    main()