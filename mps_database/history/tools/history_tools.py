import random

from sqlalchemy.sql.functions import mode
from mps_database.mps_config import MPSConfig, models
from mps_database.history.models import fault_history, input_history
from sqlalchemy import insert, select

from sqlalchemy.orm import relationship, backref

"""
class HistorySession():
    def __init__(self):

        return
"""
#use for testing
def main():
    history_class = connect_hist_db()
    conf_class = connect_conf_db()

    #tests - fault ids range from 1-2144
    test1, test2, test3, test4 = random.randint(1, 2144), random.randint(1, 2144), random.randint(1, 2144), random.randint(1, 2144)
    add_fault(history_class, test1)
    faults = [test2, test3, test4]
    add_faults(history_class, faults)

    # Ensure entries added to db
    print(get_entry_by_id(history_class, test2))
    print(get_entry_by_id(history_class, test3))
    print(get_entry_by_id(history_class, test4))

    # Get fault information from config based on history entries 
    results = get_config_fault_info(conf_class, test1)
    print(results.mappings().all())

    results = get_config_fault_info(conf_class, test4)
    print(results.mappings().all())

    results = get_last_faults(history_class)
    print(results.mappings().all())
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
    print("Adding fault ", fault_id)
    fault_insert = fault_history.FaultHistory.__table__.insert().values(fault_id=fault_id)
    history_conn.session.execute(fault_insert)
    history_conn.session.commit()
    return

def add_faults(history_conn, fault_ids):
    print("Adding faults ", fault_ids)
    faults_info = []
    for fid in fault_ids:
        faults_info.append({'fault_id': fid})
    #TODO needs engine to run multi insert?
    history_conn.last_engine.execute(fault_history.FaultHistory.__table__.insert(), faults_info)
    history_conn.session.commit()
    return           
    
def get_last_faults(history_conn, num_faults=10):
    stmt = select(fault_history.FaultHistory.id, fault_history.FaultHistory.fault_id).order_by(fault_history.FaultHistory.timestamp.desc()).limit(num_faults)
    results = history_conn.session.execute(stmt)
    return results

def get_entry_by_id(history_conn, fid):
    print("Selecting entries ", fid)
    stmt = select(fault_history.FaultHistory.timestamp).where(fault_history.FaultHistory.fault_id == fid)
    result = history_conn.session.execute(stmt)
    #TODO, this could be multiple, idk. maybe not because fids are unique
    return result.fetchone()

def get_config_fault_info(conf_conn, fault_id):
    stmt = select(models.Fault.id, models.Fault.name, models.Fault.description).where(models.Fault.id == fault_id)
    result = conf_conn.session.execute(stmt)
    return result

if __name__ == "__main__":
    main()