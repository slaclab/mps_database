import random

from mps_database.mps_config import MPSConfig, models
from mps_database.history.models import fault_history, mitigation_history, analog_history, bypass_history, input_history
from sqlalchemy import insert, select


class HistorySession():
    def __init__(self):
        self.history_conn = None
        self.conf_conn = None
        
        self.connect_conf_db()
        self.connect_hist_db()
        return

    def execute_commit(self, to_execute):
        print("executing", to_execute)
        self.history_conn.session.execute(to_execute)
        self.history_conn.session.commit()
        return
    
    def add_fault(self, message):
        """
        Adds a single fault to the fault_history table in the history database

        Message format is [type, id, oldvalue, newvalue, aux(devicestate)]
        """
        print("Adding fault ", message)
        # Set the optional auxillary data and get the official fault id
        if message.aux > 0:
            device_state = self.conf_conn.session.query(models.DeviceState).filter(models.DeviceState.id==message.aux).first().name
        else:
            device_state = None
        fault = self.conf_conn.session.query(models.Fault).filter(models.Fault.id==message.id).first()

        # Set the new state transition
        if message.new_value == 1:
            new_state, old_state = "inactive", "active"
        else:
            new_state, old_state = "active", "inactive"

        print("ds", device_state)
        fault_insert = fault_history.FaultHistory.__table__.insert().values(fault_id=fault.description, old_state=old_state, new_state=new_state, device_state=device_state)
        self.execute_commit(fault_insert)
        return

    def add_analog(self, message):
        try:
            device = self.conf_conn.session.query(models.AnalogDevice).filter(models.AnalogDevice.id==message.id).first()
            channel = self.conf_conn.session.query(models.AnalogChannel).filter(models.AnalogChannel.id==device.channel_id).first()

            # This will fail if the values are strings, not ints. TODO: see how it sends info
            old_value, new_value = hex(message.old_value), hex(message.new_value)
        except:
            print("Something went wrong with analog", message)
            return
        analog_insert = analog_history.AnalogHistory.__table__.insert().values(channel=channel.name, old_state=old_value, new_state=new_value)
        self.execute_commit(analog_insert)
        return

    def add_bypass(self, message):
        #Determine valid/expiration status
        old_name, new_name = "Valid", "Valid"
        if message.old_value == 0: old_name = "Expired"
        if message.new_value == 0: new_name = "Expired"

        if message.aux > 31:
            device_input = self.conf_conn.session.query(models.DeviceInput).filter(models.DeviceInput.id==message.id).first()
            channel = self.conf_conn.session.query(models.DigitalChannel).filter(models.DigitalChannel.id==device_input.channel_id).first()
            bypass_insert = bypass_history.BypassHistory.__table__.insert().values(bypass_id=channel.name, new_state=new_name, old_state=old_name)
        else:
            analog_device = self.conf_conn.session.query(models.AnalogDevice).filter(models.AnalogDevice.id==message.id).first()
            channel = self.conf_conn.session.query(models.AnalogChannel).filter(models.AnalogChannel.id==analog_device.channel_id).first()
            bypass_insert = bypass_history.BypassHistory.__table__.insert().values(bypass_id=channel.name, new_state=new_name, old_state=old_name, integrator=message.aux)
        self.execute_commit(bypass_insert)
        return
    
    def add_input(self, message):
        device_input = self.conf_conn.session.query(models.DeviceInput).filter(models.DeviceInput.id==message.id).first()
        channel = self.conf_conn.session.query(models.DigitalChannel).filter(models.DigitalChannel.id==device_input.channel_id).first()
        device = self.conf_conn.session.query(models.DigitalDevice).filter(models.DigitalDevice.id==device_input.digital_device_id).first()

        old_name = channel.z_name
        new_name = channel.z_name
        if (message.old_value > 0):
            old_name = channel.o_name
        if (message.new_value > 0):
            new_name = channel.o_name

        input_insert = input_history.InputHistory.__table__.insert().values(new_state=new_name, old_state=old_name, channel=channel.name, device=device.name)
        self.execute_commit(input_insert)
        return

    def add_mitigation(self, message):
        try:
            device = self.conf_conn.session.query(models.BeamDestination).filter(models.BeamDestination.id==message.id).first()
            bc1 = self.conf_conn.session.query(models.BeamClass).filter(models.BeamClass.id==message.old_value).first()
            bc2 = self.conf_conn.session.query(models.BeamClass).filter(models.BeamClass.id==message.new_value).first()
        except:
            print("Something went wrong with mitigation", message.id)
            return
        mitigation_insert = mitigation_history.MitigationHistory.__table__.insert().values(device=device.name, new_state=bc2.name, old_state=bc1.name)
        self.execute_commit(mitigation_insert)
        return

    def add_faults(self, fault_ids):
        """
        Adds a list of faults to the fault_history table in the history database
        """
        print("Adding faults ", fault_ids)
        faults_info = []
        for fid in fault_ids:
            faults_info.append({'fault_id': fid})
        #TODO needs engine to run multi insert?
        self.history_conn.last_engine.execute(fault_history.FaultHistory.__table__.insert(), faults_info)
        self.history_conn.session.commit()
        return      

    def query_beamclass(self):
        print(self.conf_conn.query(models.BeamClass.name).all())
        return

    def get_last_faults(self, num_faults=10):
        """
        Gets the ten most recent fault entries from the history database
        """
        stmt = select(fault_history.FaultHistory.id, fault_history.FaultHistory.fault_id).order_by(fault_history.FaultHistory.timestamp.desc()).limit(num_faults)
        results = self.history_conn.session.execute(stmt)
        return results

    def get_all_faults_by_id(self, fid):
        """
        Gets all fault entries in the history database based from their fid
        """
        print("Selecting entries ", fid)
        stmt = select(fault_history.FaultHistory.timestamp).where(fault_history.FaultHistory.fault_id == fid)
        result = self.history_conn.session.execute(stmt)
        return result.fetchall()

    def get_entry_by_id(self, fid):
        """
        Gets a single fault entry from history database based on its unique id
        """
        stmt = select(fault_history.FaultHistory.timestamp).where(fault_history.FaultHistory.id == fid)
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
    
def main():
    history = HistorySession()
    return


if __name__ == "__main__":
    main()