from mps_database import mps_config, models
from mps_database.history.models import analog_history, bypass_history, input_history, fault_history, mitigation_history
from mps_database.models import Base

from ctypes import *

import socket, random, pprint, struct




def main():
    tables = [analog_history.AnalogHistory.__table__, bypass_history.BypassHistory.__table__, fault_history.FaultHistory.__table__, input_history.InputHistory.__table__, mitigation_history.MitigationHistory.__table__]
    #delete_history_db(tables)
    #create_history_db(tables)

    create_socket()

    return

def create_socket():
    host = '127.0.0.1'
    #host = "192.168.0.215"
    port = 1234
    
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect((host, port))
        for data in generate_test_data():
            s.sendall(struct.pack('5I', data[0], data[1], data[2], data[3], data[4]))
    return

def generate_test_data():
    #type, fault.id, old_val, new_val, DeviceState.id(opt)
    fault = [1, random.randint(1,2144), random.randint(0,1), random.randint(0,1), 0]
    fault_aux = [1, random.randint(1,2144), random.randint(0,1), random.randint(0,1), random.randint(1, 79)]
    #BypassStateType, AnalogDevice.id, oldValue, newValue, 0
    analog_bypass = [2, random.randint(1,686), random.randint(0,1), random.randint(0,1), 0]
    #BypassStateType, DeviceInput.id, oldValue, newValue, index(>31)
    digital_bypass = [2, random.randint(1,1011), random.randint(0,1), random.randint(0,1), 32]
    #MitigationType, BeamDestination.id, BeamClass.id (oldValue), BeamClass.id (newValue), 0
    mitigation = [3, random.randint(1,4), random.randint(1,11), random.randint(1,11), 0]
    #DeviceInputType, DeviceInput.id, oldValue, newValue, 0
    input = [4, random.randint(1,1011), random.randint(0,1), random.randint(0,1), 0]
    #AnalogDeviceType, AnalogDevice.id, oldValue, newValue, 0
    #This is the one that the values convert to hex, idk what their starting vals are
    #TODO: what is this??????????
    analog = [5, random.randint(1,686), 0, 0, 0]
    test_data = [fault, fault_aux, analog_bypass, digital_bypass, mitigation, input, analog]
    pprint.pprint(test_data)
    return test_data

def create_history_db(tables):
    history_engine = mps_config.MPSConfig(db_file="mps_gun_history.db", db_name="history").last_engine
    Base.metadata.create_all(history_engine, tables=tables)
    #build_fault_table("test").__table__.create(bind = config_engine.last_engine)
    return

def delete_history_db(tables):
    #Add function to delete all tables/rows
    meta = models.Base.metadata
    meta.bind = mps_config.MPSConfig(db_file="mps_gun_history.db", db_name="history").last_engine
    meta.drop_all(tables=tables)
    return

if __name__ == "__main__":
    main()


