from mps_database import mps_config, models
from mps_database.history.tools import history_tools
from mps_database.history.models import analog_history, bypass_history, input_history, fault_history, mitigation_history
from mps_database.models import Base

from mps_database.mps_config import MPSConfig
from sqlalchemy import select

from ctypes import *

import socket, random, pprint, struct




def main():
    """
    Main function responsible for calling whatever tools functions you need. 
    """

    #tables = [analog_history.AnalogHistory.__table__, bypass_history.BypassHistory.__table__, fault_history.FaultHistory.__table__, input_history.InputHistory.__table__, mitigation_history.MitigationHistory.__table__]
    #delete_history_db(tables)
    #create_history_db(tables)

    create_socket()
    """
    hist = history_tools.HistorySession()
    print("Getting Faults")
    print(hist.get_last_faults())
    fid=3
    print("Getting Fault number ", fid)
    print(hist.get_entry_by_id(fid))
    """



    return

def create_socket():
    """
    Acts as a client to connect to HistoryServer backend. 

    Creates a socket and sends over generated test insert data.
    """
    host = '127.0.0.1'
    #host = "192.168.0.215"
    port = 1234
    
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect((host, port))
        # TODO: remove test data from this function
        for data in generate_test_data():
            s.sendall(struct.pack('5I', data[0], data[1], data[2], data[3], data[4]))
        for data in create_bad_data():
            s.sendall(struct.pack('5I', data[0], data[1], data[2], data[3], data[4]))

    return

def generate_test_data():
    """
    Generates a suite of realistic test data for entering into the history db.

    Type number 3 is skipped because it is defined as "BypassValueType" in the central node ioc, and does not appear to be relevant
    """
    conf_conn = MPSConfig(db_name="config", db_file='mps_config_imported.db')
    ad_select = select(models.AnalogDevice.id)
    ad_result = conf_conn.session.execute(ad_select)
    result = [r[0] for r in ad_result]


    #type, fault.id, old_val, new_val, DeviceState.id(opt)
    fault = [1, random.randint(1,2144), random.randint(0,1), random.randint(0,1), 0]
    fault_aux = [1, random.randint(1,2144), random.randint(0,1), random.randint(0,1), random.randint(1, 79)]
    #BypassStateType, AnalogDevice.id, oldValue, newValue, 0-31
    analog_bypass = [2, random.choice(result), random.randint(0,1), random.randint(0,1), random.randint(0, 31)]
    #BypassStateType, DeviceInput.id, oldValue, newValue, index(>31)
    digital_bypass = [2, random.randint(1,1011), random.randint(0,1), random.randint(0,1), 32]
    #MitigationType, BeamDestination.id, BeamClass.id (oldValue), BeamClass.id (newValue), 0
    mitigation = [4, random.randint(1,4), random.randint(1,11), random.randint(1,11), 0]
    #DeviceInputType, DeviceInput.id, oldValue, newValue, 0
    device_input = [5, random.randint(1,1011), random.randint(0,1), random.randint(0,1), 0]
    #AnalogDeviceType, AnalogDevice.id, oldValue, newValue, 0
    analog = [6, random.choice(result), 0, 0, 0]
    test_data = [fault, fault_aux, analog_bypass, digital_bypass, mitigation, device_input, analog]
    pprint.pprint(test_data)
    return test_data

def create_bad_data():
    fault = [1, 23, 23, 23, 0]
    analog_bypass = [2, 434343, 4, 3, 4]
    digital_bypass = [2, 1012, 1, 1, 32]
    mitigation = [4, 5, 8, 8, 0]
    device_input = [5, 1012, 2, 1, 0]
    analog = [6, 34343, 3, 0, 0]
    random_data = [54, 3, 2, 3, 2]
    
    test_data = [fault, analog_bypass, digital_bypass, mitigation, device_input, analog, random_data]
    return test_data

def create_history_db(tables):
    """
    Creates all tables to be used in the history database.
    Should not be called regularly.
    """
    history_engine = mps_config.MPSConfig(db_file="mps_gun_history.db", db_name="history").last_engine
    Base.metadata.create_all(history_engine, tables=tables)
    #build_fault_table("test").__table__.create(bind = config_engine.last_engine)
    return

def delete_history_db(tables):
    """
    Deletes all data in tables in the history database. 
    Note: Does not remove empty table definitions from db.
    """
    #Add function to delete all tables/rows
    meta = models.Base.metadata
    meta.bind = mps_config.MPSConfig(db_file="mps_gun_history.db", db_name="history").last_engine
    meta.drop_all(tables=tables)
    return

if __name__ == "__main__":
    main()


