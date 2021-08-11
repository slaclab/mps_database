import random

from sqlalchemy.sql.functions import mode
from mps_database.mps_config import MPSConfig, models
from mps_database.history.models import fault_history, input_history
from sqlalchemy import insert, select

from sqlalchemy.orm import relationship


class HistorySession():
    def __init__(self):
        self.history_conn = None
        self.conf_conn = None
        
        self.connect_conf_db()
        self.connect_hist_db()
        return

    def add_fault(self, fault_id):
        print("Adding fault ", fault_id)
        fault_insert = fault_history.FaultHistory.__table__.insert().values(fault_id=fault_id)
        self.history_conn.session.execute(fault_insert)
        self.history_conn.session.commit()
        return

    def add_faults(self, fault_ids):
        print("Adding faults ", fault_ids)
        faults_info = []
        for fid in fault_ids:
            faults_info.append({'fault_id': fid})
        #TODO needs engine to run multi insert?
        self.history_conn.last_engine.execute(fault_history.FaultHistory.__table__.insert(), faults_info)
        self.history_conn.session.commit()
        return      

    #TODO: is imported the default name now? Or is that just for testing?

    def query_beamclass(self):
        print(self.conf_conn.query(models.BeamClass.name).all())
        return

    def get_last_faults(self, num_faults=10):
        stmt = select(fault_history.FaultHistory.id, fault_history.FaultHistory.fault_id).order_by(fault_history.FaultHistory.timestamp.desc()).limit(num_faults)
        results = self.history_conn.session.execute(stmt)
        return results

    def get_entry_by_id(self, fid):
        print("Selecting entries ", fid)
        stmt = select(fault_history.FaultHistory.timestamp).where(fault_history.FaultHistory.fault_id == fid)
        result = self.history_conn.session.execute(stmt)
        #TODO, this could be multiple, idk. maybe not because fids are unique
        return result.fetchone()

    def get_config_fault_info(self, fault_id):
        stmt = select(models.Fault.id, models.Fault.name, models.Fault.description).where(models.Fault.id == fault_id)
        result = self.conf_conn.session.execute(stmt)
        return result
     
    def connect_hist_db(self):
        self.history_conn = MPSConfig(db_name="history", db_file='mps_gun_history.db')
        return

    def connect_conf_db(self):
        # gun, runtime dbs hardcoded for now
        #TODO: add cli args later
        self.conf_conn = MPSConfig(db_name="config", db_file='mps_config_imported.db')
        return
    




#use for testing
def main():
    history = HistorySession()

    #tests - fault ids range from 1-2144
    test1, test2, test3, test4 = random.randint(1, 2144), random.randint(1, 2144), random.randint(1, 2144), random.randint(1, 2144)
    history.add_fault(test1)
    faults = [test2, test3, test4]
    history.add_faults(faults)

    # Ensure entries added to db
    print(history.get_entry_by_id(test2))
    print(history.get_entry_by_id(test3))
    print(history.get_entry_by_id(test4))

    # Get fault information from config based on history entries 
    results = history.get_config_fault_info(test1)
    print(results.mappings().all())

    results = history.get_config_fault_info(test4)
    print(results.mappings().all())

    results = history.get_last_faults()
    print(results.mappings().all())
    return


if __name__ == "__main__":
    main()