import random

from sqlalchemy.sql.functions import mode
from mps_database.mps_config import MPSConfig, models
from mps_database.history.models import fault_state, device_input
from sqlalchemy import insert, select

from sqlalchemy.orm import relationship


class HistorySession():
    def __init__(self):
        self.history_conn = None
        self.conf_conn = None
        
        self.connect_conf_db()
        self.connect_hist_db()
        return

    def add_fault(self, message):
        """
        Adds a single fault to the fault_state table in the history database

        Message format is [type, id, oldvalue, newvalue, aux(devicestate)]
        """
        print("Adding fault ", message[1])
        if message[-1] > 0:
            device_state = message[-1]
        else:
            device_state = None
        fault_insert = fault_state.FaultState.__table__.insert().values(fault_id=message[1], old_state=message[2], new_state=message[3], device_state=device_state)
        self.history_conn.session.execute(fault_insert)
        self.history_conn.session.commit()
        return

    def add_faults(self, fault_ids):
        """
        Adds a list of faults to the fault_state table in the history database
        """
        print("Adding faults ", fault_ids)
        faults_info = []
        for fid in fault_ids:
            faults_info.append({'fault_id': fid})
        #TODO needs engine to run multi insert?
        self.history_conn.last_engine.execute(fault_state.FaultState.__table__.insert(), faults_info)
        self.history_conn.session.commit()
        return      

    def query_beamclass(self):
        print(self.conf_conn.query(models.BeamClass.name).all())
        return

    def get_last_faults(self, num_faults=10):
        """
        Gets the ten most recent fault entries from the history database
        """
        stmt = select(fault_state.FaultState.id, fault_state.FaultState.fault_id).order_by(fault_state.FaultState.timestamp.desc()).limit(num_faults)
        results = self.history_conn.session.execute(stmt)
        return results

    def get_all_faults_by_id(self, fid):
        """
        Gets all fault entries in the history database based from their fid
        """
        print("Selecting entries ", fid)
        stmt = select(fault_state.FaultState.timestamp).where(fault_state.FaultState.fault_id == fid)
        result = self.history_conn.session.execute(stmt)
        return result.fetchall()

    def get_entry_by_id(self, fid):
        """
        Gets a single fault entry from history database based on its unique id
        """
        stmt = select(fault_state.FaultState.timestamp).where(fault_state.FaultState.id == fid)
        result = self.history_conn.session.execute(stmt)
        return result.fetchone()

    def get_config_fault_info(self, fault_id):
        """
        Gets some descriptive information of one fault from the configuration database based on fault id
        """
        stmt = select(models.Fault.id, models.Fault.name, models.Fault.description).where(models.Fault.id == fault_id)
        result = self.conf_conn.session.execute(stmt)
        return result
     
    def connect_hist_db(self):
        """
        Creates a interactable connection to the history database
        """
        self.history_conn = MPSConfig(db_name="history", db_file='mps_gun_history.db')
        return

    def connect_conf_db(self):
        """
        Creates a interactable connection to the configuration database
        """
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
    print("Selecting multiple faults for ", test2)
    print(history.get_all_faults_by_id(test2))
    print("Get single entry of unique id ", 4)
    print(history.get_entry_by_id(4))
    #print(history.get_entry_by_id(test4))

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