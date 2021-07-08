from mps_database.mps_config import MPSConfig, models
from mps_database.tools.mps_names import MpsName
from sqlalchemy import func, exc
import argparse
import os
import errno
import re
import shutil
from pprint import *

class MpsDbReader:
    """
    This class is used to open a session to the MPS Database,
    making sure that the it is properly closed at the end.

    It is intended to be called in a 'with-as' code block.
    """
    def __init__(self, db_file):
        self.db_file = db_file

    def __enter__(self):
        # Open the MPS database
        self.mps_db = MPSConfig(self.db_file)

        # Return a session to the database
        return self.mps_db.session

    def __exit__(self, exc_type, exc_value, traceback):
        # Close the MPS database
        self.mps_db.session.close()


class MpsAppReader:
    """
    This class extract all the necessary information of each application
    defined in the MPS database, necessary to generate EPICS Databases,
    configuration files, and GUI screens.
    """
#    def __init__(self, db_file, template_path, dest_path, app_id, verbose):
    def __init__(self, db_file='', app_id=None, verbose=False):

        self.app_id = app_id 
        self.verbose = verbose
        self.cn0 = [8,9,10,11]
        self.cn1 = [12,13,14,15,16,17,18,19,20,21,22,23]
        self.cn2 = [0,1,2,3,4,5,6,7]


        # This is the list of all applications
        self.analog_apps = []
        self.digital_apps= []
        self.beam_classes = []
        self.beam_destinations = []
        self.conditions = []
        
        # List of Link Nodes by cpu_name + slot - track if it has only digital, analog or both apps
        self.link_nodes = {}

        self.config_version = os.path.basename(db_file).lstrip("mps_config-").rstrip(".db")

        # Open a session to the MPS database
        with MpsDbReader(db_file) as mps_db_session:

            # Extract the application information
            self.mps_name = MpsName(mps_db_session)
            self.__extract_apps(mps_db_session)
            self.__extract_destinations(mps_db_session)
            self.__extract_conditions(mps_db_session)

    def __add_slot_information_by_name(self, mps_db_session, ln_name, app_card):
        slot_number = app_card.slot_number
        if self.link_nodes[ln_name]['type'] == 'Digital' and slot_number == 2:
          slot_number = 1
        
        slot_info = {}
        slot_info['pv_base'] = app_card.get_pv_name()
        slot_info['app_id'] = app_card.global_id
        
        slot_info = {}
        slot_info['pv_base'] = app_card.get_pv_name()
        slot_info['app_id'] = app_card.global_id

        try:
            app_type = mps_db_session.query(models.ApplicationType).\
                filter(models.ApplicationType.id == app_card.type_id).one()
            app_description = app_card.get_app_description()
        except exc.SQLAlchemyError as e:
            raise

        slot_info['type'] = app_type.name
        slot_info['description'] = app_description
        if slot_info['type'] == "Digital Card":
          slot_number = 1
        if slot_number in self.link_nodes[ln_name]['slots']:
          print(('ERROR: Found multiple apps in same slot: link node {}, slot {}'.\
                      format(ln_name, app_card.slot_number)))
          exit(1)
        self.link_nodes[ln_name]['slots'][slot_number] = slot_info

    def __add_slot_information_by_crate(self, mps_db_session, ln_name, crat, app_card):
        if app_card.slot_number in self.link_nodes[ln_name]['slots']:
            print(('ERROR: Found multiple apps in same slot: link node {}, slot {}'.\
                      format(ln_name, app_card.slot_number)))
            exit(1)
        
        slot_info['type'] = app_type.name
        slot_info['description'] = app_description
        if slot_info['type'] == "Digital Card":
          slot_number = 1
        if slot_number in self.link_nodes[ln_name]['slots']:
          print(('ERROR: Found multiple apps in same slot: link node {}, slot {}'.\
                      format(ln_name, app_card.slot_number)))
          exit(1)
        self.link_nodes[ln_name]['slots'][slot_number] = slot_info

        try:
            app_type = mps_db_session.query(models.ApplicationType).\
                filter(models.ApplicationType.id == app_card.type_id).one()
        except exc.SQLAlchemyError as e:
            raise

        slot_info['type'] = app_type.name
        self.link_nodes[ln_name]['slots'][app_card.slot_number] = slot_info

    def __extract_destinations(self, mps_db_session):
        try:
            # Get all the apps defined in the database
            destinations = mps_db_session.query(models.BeamDestination).all()
            beamClasses = mps_db_session.query(models.BeamClass).all()
        except exc.SQLAlchemyError as e:
            raise

        for beamClass in beamClasses:
          beam_data = {}
          beam_data["id"] = beamClass.id
          beam_data["number"] = beamClass.number
          beam_data["name"] = beamClass.name
          beam_data["description"] = beamClass.description
          beam_data["integration_window"] = beamClass.integration_window
          beam_data["min_period"] = beamClass.min_period
          beam_data["total_charge"] = beamClass.total_charge
          self.beam_classes.append(beam_data)
        for dest in destinations:
          dest_data = {}
          dest_data["id"] = dest.id
          dest_data["name"] = dest.name
          dest_data["description"] = dest.description
          dest_data["destination_mask"] = dest.destination_mask
          self.beam_destinations.append(dest_data)

    def __extract_conditions(self, mps_db_session):
        try:
            # Get all the apps defined in the database
            conditions = mps_db_session.query(models.Condition).all()
        except exc.SQLAlchemyError as e:
            raise      
        for cond in conditions:
          cond_data = {}
          cond_data["name"] = cond.name.upper()
          cond_data["description"] = cond.description
          cond_data["db_id"] = cond.id
          self.conditions.append(cond_data)
        

    def __extract_apps(self, mps_db_session):
        """
        Extract all application information from the MPS database. A session to the
        database is passed as an argument.

        The result will be 2 lists off application data, one for analog and one
        for digital application.

        List of analog applications:

        Each application data will be a dictionary with the following structure:
        - app_id (number)
        - cpu_name (str)
        - crate_id (number)
        - slot_n (number)
        - link_node_area (str)
        - link_node_location (str)
        - card_index (number)
        - devices (list)
        - central_node (number) (0 = B005 slot 2, 1 = B005 slot 3, 2 = B005 slot 2 and LI00)

        Each device in the application devices list will be a dictionary with
        the following structure:
        - type_name (str)
        - bay_number (number)
        - area (str)
        - position (str)
        - cable (str)
        - slope (float) analog calibration slope to mV
        - offset (float) analog calibration offset to mV
        - faults (dict)
        - db_id (number) the analog device ID

        The device faults dictionary will be have keys equal to the fault ID, and the
        values will be dictionary with the following structure:
        - name (str)
        - description (str)
        - bit_positions (list)
        - mask (list)
        - integrator (list)

        The bit_position list will holds all the bit_position used by the same fault ID.

        List of digital applications:

        Each application data will be a dictionary with the following structure:
        - app_id (number)
        - cpu_name (str)
        - crate_id (number)
        - slot_n (number)
        - link_node_area (str)
        - link_node_location (str)
        - card_index (number)
        - central_node (number) (0 = B005 slot 2, 1 = B005 slot 3, 2 = B005 slot 2 and LI00)
        - devices (list)

        Each device in the application devices list will be a dictionary with
        the following structure:
        - type_name (str)
        - area (str)
        - position (str)
        - inputs (list)
        - faults (dict)

        Each input in the device inputs list will be a dictionary with
        the following structure:
        - name (str)
        - bit_position (number)
        - zero_name (str)
        - one_name (str)
        - alarm_state (number)
        - debounce (number)

        The device faults dictionary will be have keys equal to the fault ID, and the
        values will be dictionary with the following structure:
        - name (str)
        - description (str)
        - bit_positions (list)
        - mask (list)
        - integrator (list)
        """

        try:
            # Get all the apps defined in the database
            if (self.app_id == None):
                app_cards = mps_db_session.query(models.ApplicationCard).all()
            else:
                app_cards = mps_db_session.query(models.ApplicationCard).\
                    filter(models.ApplicationCard.global_id == self.app_id).all()
            link_nodes = mps_db_session.query(models.LinkNode).all()
        except exc.SQLAlchemyError as e:
            raise

        if (len(link_nodes) > 0):
            for ln in link_nodes:
                name = ln.get_name()
                cr = ln.crate.id
                ln_type = ln.get_type()
                ln_app_prefix = ln.get_app_prefix()
                ln_group = ln.get_ln_group()
                self.link_nodes[name] = {}
                self.link_nodes[name]['type'] = ln_type # 'Analog', 'Digital' or 'Mixed'
                self.link_nodes[name]['slots'] = {}
                self.link_nodes[name]['app_prefix'] = ln_app_prefix
                self.link_nodes[name]['physical'] = "Not Installed"
                self.link_nodes[name]['group'] = ln_group
                self.link_nodes[name]['shm_name'] = ln.get_shelf_manager()
                self.link_nodes[name]['cn_prefix'] = self.get_cn_prefix(ln_group)
                self.link_nodes[name]['analog_slot'] = 2
                self.link_nodes[name]['group_link'] = ln.group_link
                self.link_nodes[name]['group_link_destination'] = ln.group_link_destination
                self.link_nodes[name]['crate_index'] = cr

                #self.link_nodes[cr] = {}
                #self.link_nodes[cr]['type'] = ln_type # 'Analog', 'Digital' or 'Mixed'
                #self.link_nodes[cr]['slots'] = {}
                #self.link_nodes[cr]['app_prefix'] = ln_app_prefix

        # Check if there were applications defined in the database
        if len(app_cards) == 0:
            return

        # Iterate over all the found applications
        for app_card in app_cards:

            # Look for all devices in this application
            devices = app_card.devices

            # Extract analog and digital devices
            analog_devices = []
            digital_devices= []
            for device in devices:

                if type(device) is models.device.AnalogDevice:
                    analog_devices.append(device)

                if type(device) is models.device.DigitalDevice:
                    digital_devices.append(device)
            # Process the analog devices
            if len(analog_devices):

                ln_name = app_card.link_node.get_name()
                phys = app_card.crate.location
                #ln_name = app_card.crate.location

                # Get this application data
                app_data = {}
                app_data["app_id"] = app_card.global_id
                app_data["db_id"] = app_card.id
                app_data["cpu_name"] = app_card.link_node.cpu
                app_data["crate_id"] = app_card.crate.crate_id
                app_data["crate_key"] = app_card.link_node.crate_id
                app_data["slot_number"] = app_card.slot_number
                app_data["link_node_name"] = ln_name
                app_data["physical"] = phys
                app_data["link_node_area"] = app_card.link_node.area
                app_data["link_node_location"] = app_card.link_node.location
                app_data["card_index"] = app_card.get_card_id()
                app_data["lc1_node_id"] = str(app_card.link_node.lcls1_id)
                app_data["app_prefix"] = app_card.get_pv_name()
                app_data['link_node_name_prev'] = app_card.link_node.get_name()
                app_data["name"] = app_card.name
                app_data['central_node'] = self.get_cn_index(app_card.link_node.group)


                self.link_nodes[ln_name]["lc1_node_id"] = app_data["lc1_node_id"]
                self.link_nodes[ln_name]["crate_id"] = app_data["crate_id"]
                self.link_nodes[ln_name]["cpu_name"] = app_data["cpu_name"]
                self.link_nodes[ln_name]["physical"] = app_data["physical"]
                self.link_nodes[ln_name]["sioc"] = ln_name

                #self.link_nodes[phys]["lc1_node_id"] = app_data["lc1_node_id"]
                #self.link_nodes[phys]["crate_id"] = app_data["crate_id"]
                #self.link_nodes[phys]["cpu_name"] = app_data["cpu_name"]
                #self.link_nodes[phys]["physical"] = app_data["physical"]
                #self.link_nodes[phys]["sioc"] = ln_name

                self.__add_slot_information_by_name(mps_db_session, ln_name, app_card)
                #self.__add_slot_information_by_crate(mps_db_session, phys, app_card)

                # Defines whether the IOC_NAME env var should be added no the mps.env
                # file. In order to add only once we need to figure out if there are
                # other cards with the same SIOC. If there is a digital card the SIOC
                # is written in the digital section. If a card is a "Generic ADC" and
                # it is not in slot 2 then it has its own SIOC (there are only ~7 cases
                # like that)
                app_data["analog_link_node"] = False
                if (app_card.link_node.slot_number != 2 and app_card.name == "Generic ADC"):
                    app_data["analog_link_node"] = True # Non-slot 2 link node
                    self.link_nodes[ln_name]['analog_slot'] = app_card.link_node.slot_number
                    #self.link_nodes[phys]['analog_slot'] = app_card.link_node.slot_number
                elif (app_card.link_node.slot_number == 2):
                    self.link_nodes[ln_name]['analog_slot'] = 2
                    #self.link_nodes[phys]['analog_slot'] = 2
                    has_digital = False
                    for c in app_card.link_node.cards:
                        if (c.name == "Digital Card" or c.name == "Generic ADC" and c.id != app_card.id):
                            has_digital = True

                    if (not has_digital):
                        app_data["analog_link_node"] = True # Add if the digital card is not defined

                app_data["devices"] = []

                # Iterate over all the analog devices in this application
                for device in analog_devices:

                    # Look for fault inputs in this device
                    fault_inputs = device.fault_outputs

                    # Check if this devices has faults. Only devices with defined faults will be included
                    if len(fault_inputs):

                        # get this device data
                        device_data = {}
                        device_data["type_name"] = self.__get_device_type_name(mps_db_session, device.device_type_id)
                        device_data["bay_number"], device_data["channel_number"], device_data["channel_index"] = \
                            self.__get_bay_ch_number(mps_db_session, device.channel_id, app_card.type_id)
                        device_data["area"] = device.area
                        device_data["position"] = device.position
                        device_data["faults"] = {}
                        device_data["device_name"] = device.name
                        device_data["cable"] = device.cable_number
                        device_data["offset"] = device.offset
                        device_data["slope"] = device.slope
                        device_data["prefix"] = '{0}'.format(self.mps_name.getAnalogDeviceNameFromId(device.id))
                        device_data["db_id"] = device.id
                        device_data["channel"] = device.channel.number

                        # Iterate over all the faults in this device
                        for fault_input in fault_inputs:
                            faults = mps_db_session.query(models.Fault).filter(models.Fault.id==fault_input.fault_id).all()
                            if (len(faults) != 1):
                                print('ERROR: Fault not defined')
                                exit(-1)
                            fault_states = mps_db_session.query(models.FaultState).\
                                filter(models.FaultState.fault_id==faults[0].id).all()

                            # Get the fault ID
                            fault_id = fault_input.fault_id

                            # Get this fault data
                            if (not fault_id in device_data["faults"]):
                                # Get the fault corresponding to this fault input.
                                fault = self.__get_fault(mps_db_session, fault_id)
                                fault_data = {}
                                fault_data["id"] = fault_id
                                fault_data["name"] = fault.name
                                fault_data["description"] = fault.description[:39]
                                fault_data["bit_positions"] = []
                                fault_data["integrators"] = []
                                fault_data["mask"] = []
                                fault_data["states"] = []
                                fault_data["fs_id"] = []
                                fault_data["fs_desc"] = []
                                for fs in fault_states:
                                    fault_data["bit_positions"].append(fs.device_state.get_bit_position())
                                    fault_data["integrators"].append(fs.device_state.get_integrator())
                                    fault_data["mask"].append(fs.device_state.mask)
                                    fault_data["states"].append(fs.device_state.name)
                                    fault_data["fs_id"].append(fs.id)
                                    fault_data["fs_desc"].append(fs.device_state.description)
 
                                # Add this fault to the list of faults of the current device
                                device_data["faults"][fault_id] = fault_data

                        # Add this device to the list of devices of the current application
                        app_data["devices"].append(device_data)



                # Add this application to the list of applications, if its list of devices is not empty
                # The list of devices will be empty if not device in this app have defined fault inputs,
                # as devices without faults inputs won't be processed.
                if app_data["devices"]:
                    self.analog_apps.append(app_data)

            # Process the digital devices
            if len(digital_devices):

                ln_name = app_card.link_node.get_name()
                phys = app_card.crate.location

                # Get this application data
                app_data = {}
                app_data["app_id"] = app_card.global_id
                app_data["db_id"] = app_card.id
                app_data["cpu_name"] = app_card.link_node.cpu
                app_data["crate_id"] = app_card.crate.crate_id
                app_data["crate_key"] = app_card.crate.id
                app_data["slot_number"] = app_card.slot_number
                app_data["link_node_area"] = app_card.link_node.area
                app_data["link_node_name"] = ln_name
                app_data["physical"] = phys
                app_data["link_node_location"] = app_card.link_node.location
                app_data["card_index"] = app_card.get_card_id()
                app_data["virtual"] = False
                app_data["lc1_node_id"] = str(app_card.link_node.lcls1_id)
                app_data["app_prefix"] = app_card.get_pv_name()
                app_data['central_node'] = self.get_cn_index(app_card.link_node.group)
                app_data["name"] = app_card.name
                app_data["devices"] = []
                if (app_card.has_virtual_channels()):
                    app_data["virtual"] = True

                self.link_nodes[ln_name]["lc1_node_id"] = app_data["lc1_node_id"]
                self.link_nodes[ln_name]["crate_id"] = app_data["crate_id"]
                self.link_nodes[ln_name]["cpu_name"] = app_data["cpu_name"]
                self.link_nodes[ln_name]["dig_app_id"] = app_data["app_id"]
                self.link_nodes[ln_name]["physical"] = app_data["physical"]
                self.link_nodes[ln_name]["sioc"] = ln_name
                if self.link_nodes[ln_name]['type'] == 'Digital':
                  self.link_nodes[ln_name]['analog_slot'] = 2
                self.__add_slot_information_by_name(mps_db_session, ln_name, app_card)
                #self.link_nodes[phys]["lc1_node_id"] = app_data["lc1_node_id"]
                #self.link_nodes[phys]["crate_id"] = app_data["crate_id"]
                #self.link_nodes[phys]["cpu_name"] = app_data["cpu_name"]
                #self.link_nodes[phys]["dig_app_id"] = app_data["app_id"]
                #self.link_nodes[phys]["physical"] = app_data["physical"]
                #self.link_nodes[phys]["sioc"] = ln_name

                # Iterate over all the analog devices in this application
                for device in digital_devices:

                    # Look for all the inputs in this device
                    inputs = device.inputs
                    fault_inputs = device.fault_outputs

                    # Check if this device has inputs. Only devices with inputs defined will be included
                    if len(inputs):

                        # get this device data
                        device_data = {}
                        device_data["type_name"] = self.__get_device_type_name(mps_db_session, device.device_type_id)
                        device_data["area"] = device.area
                        device_data["position"] = device.position
                        device_data["inputs"] = []
                        device_data["device_name"] = device.name
                        device_data["faults"] = []
                        device_data["prefix"] = '{}:{}:{}'.format(self.get_prefix(device_data["type_name"]), device.area, device.position)

                        for input in inputs:
                            # Get the digital channel
                            digital_channel = self.__get_digital_channel(mps_db_session, input.channel_id)

                            # Get this channel data
                            input_data = {}
                            input_data["name"] = digital_channel.name
                            input_data["bit_position"] = digital_channel.number
                            input_data["zero_name"] = digital_channel.z_name
                            input_data["one_name"] = digital_channel.o_name
                            input_data["alarm_state"] = digital_channel.alarm_state
                            input_data["debounce"] = digital_channel.debounce
                            input_data["db_id"] = digital_channel.id
                            if (digital_channel.num_inputs == 1):
                                input_data["input_pv"] = digital_channel.monitored_pvs
                            else:
                                if device.measured_device_type_id is not None:
                                  pv_device_type = self.__get_device_type_name(mps_db_session, device.measured_device_type_id)
                                else:
                                  pv_device_type = self.__get_device_type_name(mps_db_session, device.device_type_id)
                                input_data["input_pv"] = '{0}:{1}:{2}:{3}'.format(pv_device_type,device.area, device.position, digital_channel.name)
                            if (digital_channel.alarm_state == 0):
                                input_data["zero_severity"] = "MAJOR"
                                input_data["one_severity"] = "NO_ALARM"
                            else:
                                input_data["zero_severity"] = "NO_ALARM"
                                input_data["one_severity"] = "MAJOR"

                            # Add this input to the list of inputs of the current device
                            device_data["inputs"].append(input_data)
                        
                        if len(fault_inputs):
                          for fault_input in fault_inputs:
                            faults = mps_db_session.query(models.Fault).filter(models.Fault.id==fault_input.fault_id).all()
                            if (len(faults) != 1):
                                print('ERROR: Fault not defined')
                                exit(-1)
                            fault_states = mps_db_session.query(models.FaultState).\
                                filter(models.FaultState.fault_id==faults[0].id).all()
                           # Get the fault ID
                            fault_id = fault_input.fault_id

                            # Get this fault data
                            if (not fault_id in device_data["faults"]):
                                # Get the fault corresponding to this fault input.
                                fault = self.__get_fault(mps_db_session, fault_id)
                                fault_data = {}
                                fault_data["id"] = fault_id
                                fault_data["name"] = fault.name
                                fault_data["description"] = fault.description[:39]
                                fault_data["states"] = []
                                fault_data["fs_id"] = []
                                fault_data["fs_desc"] = []
                                for fs in fault_states:
                                    fault_data["states"].append(fs.device_state.name)
                                    fault_data["fs_id"].append(fs.id)
                                    fault_data["fs_desc"].append(fs.device_state.description)
 
                                # Add this fault to the list of faults of the current device
                                device_data["faults"].append(fault_data) 
                          

                        # Add this device to the list of devices of the current application
                        app_data["devices"].append(device_data)


                # Add this application to the list of applications, if its list of devices is not empty
                # The list of devices will be empty if not device in this app have defined fault inputs,
                # as devices without faults inputs won't be processed.
                if app_data["devices"]:
                    self.digital_apps.append(app_data)
        for app_card in app_cards:
            ln_name = app_card.link_node.get_name()
            if (app_card.link_node.slot_number != 2 and app_card.name == "Generic ADC"):
                for ln_names, ln in list(self.link_nodes.items()):
                  if ln["physical"] != "Not Installed":
                    if ln["physical"] == self.link_nodes[ln_name]['physical']:
                        if ln_name != ln_names:
                            #print self.link_nodes[ln_name]['physical']
                            self.__add_slot_information_by_name(mps_db_session, ln_names, app_card)

    def pretty_print(self):
        pp=PrettyPrinter(indent=4)
        print('=== Digital Apps ===')
        pp.pprint(self.digital_apps)
        print('=== Analog Apps ===')
        pp.pprint(self.analog_apps)
        print('=== Link Nodes ===')
        pp.pprint(self.link_nodes)

    def get_cn_index(self, index):
        if index in self.cn0:
          return 0
        elif index in self.cn1:
          return 1
        elif index in self.cn2:
          return 2
        else:
          return -1

    def get_cn_prefix(self, index):
        if index in self.cn0:
          return 'SIOC:SYS0:MP01'
        elif index in self.cn1:
          return 'SIOC:SYS0:MP02'
        elif index in self.cn2:
          return 'SIOC:SYS0:MP01'
        else:
          return None      

    def get_prefix(self,typ):
      if typ in ['BDSW','BDST']:
        return 'BEND'
      elif typ in ['KCST','KICK']:
        return 'KICK'
      elif typ in ['QDSW']:
        return 'QUAD'
      else:
        return typ


    def print_app_data(self):
        """
        Print the content of the application data obtained by the extract_apps method.
        """
        print("===================================")
        print("==            RESULTS:           ==")
        print("===================================")

        # Analog application results
        print("--------------------------")
        print("--  Analog applications --")
        print("--------------------------")
        print(("Number of analog application processed: {}".format(len(self.analog_apps))))
        if (self.verbose):
            for app in self.analog_apps:
                print("  Application data:")
                print("  - - - - - - - - - - - - -")
                print(('  - EPICS PREFIX: MPLN:{}:{}:{}'.format(app["link_node_area"].upper(), app["link_node_location"].upper(), app["card_index"])))
                print(("  - App ID             : {}".format(app["app_id"])))
                print(("  - Cpu name           : {}".format(app["cpu_name"])))
                print(("  - Crate ID           : {}".format(app["crate_id"])))
                print(("  - Slot number        : {}".format(app["slot_number"])))
                print(("  - Link node name     : {}".format(app["link_node_name"])))
                print(("  - Link node area     : {}".format(app["link_node_area"])))
                print(("  - Link node location : {}".format(app["link_node_location"])))
                print(("  - Card index         : {}".format(app["card_index"])))
                print(("  - Number of devices  : {}".format(len(app["devices"]))))
                for device in app["devices"]:
                    print("    Device data:")
                    print("    .....................")
                    print(("      - EPICS PREFIX: {}:{}:{}".format(device["type_name"], device["area"], device["position"])))
                    print(("      - Type name        : {}".format(device["type_name"])))
                    print(("      - Bay number       : {}".format(device["bay_number"])))
                    print(("      - Channel number   : {}".format(device["channel_number"])))
                    print(("      - Area             : {}".format(device["area"])))
                    print(("      - Position         : {}".format(device["position"])))
                    print(("      - Number of faults : {}".format(len(device["faults"]))))
                    for fault_id,fault_data in list(device["faults"].items()):
                        print("      Fault data:")
                        print("      . . . . . . . . . . . . ")
                        print(("        - EPICS PREFIX: {}_T{}".format(fault_data["name"], fault_data["bit_positions"][0])))
                        print(("        - ID            : {}".format(fault_id)))
                        print(("        - Name          : {}".format(fault_data["name"])))
                        print(("        - Description   : {}".format(fault_data["description"])))
                        print(("        - Bit positions : {}".format(fault_data["bit_positions"])))
                        print("      . . . . . . . . . . . . ")
                    print("    .....................")
                print("  - - - - - - - - - - - - -")
                print("")
            print("--------------------------")

        # Digital application result
        print("----------------------------")
        print("--  Digital applications  --")
        print("----------------------------")
        print(("Number of digital application processed: {}".format(len(self.digital_apps))))
        if (self.verbose):
            for app in self.digital_apps:
                print("  Application data:")
                print("  - - - - - - - - - - - - -")
                print(('  - EPICS PREFIX: MPLN:{}:{}:{}'.format(app["link_node_area"].upper(), app["link_node_location"].upper(), app["card_index"])))
                print(("  - App ID             : {}".format(app["app_id"])))
                print(("  - Cpu name           : {}".format(app["cpu_name"])))
                print(("  - Crate ID           : {}".format(app["crate_id"])))
                print(("  - Slot number        : {}".format(app["slot_number"])))
                print(("  - Link node name     : {}".format(app["link_node_name"])))
                print(("  - Link node area     : {}".format(app["link_node_area"])))
                print(("  - Link node location : {}".format(app["link_node_location"])))
                print(("  - Card index         : {}".format(app["card_index"])))
                print(("  - Number of devices  : {}".format(len(app["devices"]))))
                for device in app["devices"]:
                    print("    Device data:")
                    print("    .....................")
                    print(("      - EPICS PREFIX: {}:{}:{}".format(device["type_name"], device["area"], device["position"])))
                    print(("      - Type name        : {}".format(device["type_name"])))
                    print(("      - Area             : {}".format(device["area"])))
                    print(("      - Position         : {}".format(device["position"])))
                    print(("      - Number of inputs : {}".format(len(device["inputs"]))))
                    for input in device["inputs"]:
                        print("      Input data:")
                        print("      . . . . . . . . . . . . ")
                        print(("        - EPICS PREFIX: {}".format(input["name"])))
                        print(("        - Name         : {}".format(input["name"])))
                        print(("        - Bit position : {}".format(input["bit_position"])))
                        print(("        - Zero name    : {}".format(input["zero_name"])))
                        print(("        - One name     : {}".format(input["one_name"])))
                        print(("        - Alarm state  : {}".format(input["alarm_state"])))
                        print(("        - Debounce     : {}".format(input["debounce"])))
                        print("      . . . . . . . . . . . . ")
                    print("    .....................")
                print("  - - - - - - - - - - - - -")
                print("")
            print("----------------------------")


        print("===================================")

        print(('Found {} link nodes:'.format(len(self.link_nodes))))
        for k,v in list(self.link_nodes.items()):
            print(('{}: {}'.format(k, v['type'])))

    def __get_scale_units(self, device_type_name, channel_number):
        """
        Get the engineering units used for the scale factor PVs (slope/offset).
        The unit varies based on the device type and the channel number.
        """
        if device_type_name == "BPMS":
            if channel_number == 0:
                fault_name = "X"
            elif channel_number == 1:
                fault_name = "Y"
            elif channel_number == 2:
                fault_name = "CHRG"
            else:
                raise ValueError("Function \"get_app_name(device_type_name={}, channel_number={})\". Invalid channel number for BPMS device type"
                                 .format(device_type_name, channel_number))
            return self.__get_app_units(device_type_name, fault_name)
        else:
            return self.__get_app_units(device_type_name, "")

    def get_fault_base(self, fault):
        out = fault.split('_')
        val = fault
        if out[len(out)-1] in ['T0', 'T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7']:
          val = '{0}'.format(out[0])
          for index in range(1,len(out)-1):
            val = '{0}_{1}'.format(val,out[index])
        return val     

    def get_app_units(self, device_type_name, fault_name):
        """
        Get the application enginering units used in the EPICS DB.
        The unit is application and fault specific as follows:
          * SOLN, BEND, PBLM, LBLM, BLM, BLEN => uA
          * BPMS
            - X, Y     => mm
            - CHRG     => pC
          * TORO, FARC => Nel
        """

        if device_type_name in ["SOLN", "BEND","BLEN","KICK"]:
            # Solenoid devices use 'uA'.
            return "GeV/c"
        elif device_type_name in ["BLM","LBLM","CBLM","PBLM"]:
            # Beam loss monitors set threshold in Volts initially
            return "mV"
        elif device_type_name == "BPMS":
            # For BPM, the units depend on the type of fault
            if fault_name in ["X", "Y"]:
                # Fault X, Y use 'mm'
                return "mm"
            elif fault_name == "CHRG":
                # TIMIT uses 'Nel'
                return "pC"
            else:
                raise ValueError("Function \"__get_app_units(device_type_name={}, fault_name={})\". Invalid fault name"
                    .format(device_type_name, fault_name))

        elif device_type_name in ["FARC", "TORO"]:
            # BCM devices use 'Nel'
            return "Nel"
        else:
            raise ValueError("Function \"__get_app_units(device_type_name={}, fault_name={})\". Invalid device type name"
                    .format(device_type_name, fault_name))
    def get_slope(self, device_type_name):
        """
        Get the application slope for MPS applications
          * PBLM, LBLM, BLM, BLEN => 1.6 V full scale, 65536 ADC counts full scale
          * SOLN, BEND, BLEN, KICK => units of uA
        """

        if device_type_name in ["SOLN", "BEND","BLEN","KICK"]:
            # Solenoid devices use 'uA'.
            return 0.00055586
        elif device_type_name in ["BLM","LBLM","CBLM","PBLM"]:
            # Beam loss monitors set threshold in Volts initially
            return 1.6/65536
        else:
            raise ValueError("Function \"__get_slope(device_type_name={}, fault_name={})\". Invalid device type name"
                    .format(device_type_name, fault_name))

    def get_offset(self, device_type_name):
        """
        Get the application slope for MPS applications
          * PBLM, LBLM, BLM, BLEN => should be 0
          * SOLN, BEND, BLEN, KICK => should be 0
        """

        if device_type_name in ["SOLN", "BEND","BLEN","KICK"]:
            # Solenoid devices use 'uA'.
            return 0
        elif device_type_name in ["BLM","LBLM","CBLM","PBLM"]:
            # Beam loss monitors set threshold in Volts initially
            return 0
        else:
            raise ValueError("Function \"__get_offset(device_type_name={}, fault_name={})\". Invalid device type name"
                    .format(device_type_name, fault_name))


    def get_fault_index(self, device_type_name, fault_name, channel_number):
        """
        Get the 'fault_index' used in the EPICS DB.
        The fault index is appication specific as follows:
          * SOLN, BEND, PBLM, LBLM, BLM => (X)(Y), X=input channel(0-2), Y=Integration channel (0-3)
          * BPM     => (X),    X=Channel (0:X, 1:Y, 2, CHRG)
          * TORO,FC => (X),    X=Channel (0:Charge, 1:Difference)
          * BLEN    => 0
        """
        if device_type_name in ["SOLN", "BEND", "BLEN", "KICK"]:
            integration_channel = 0
            return "{}{}".format(channel_number,integration_channel)
        elif device_type_name in ["PBLM", "CBLM", "LBLM", "BLM"]:
            # For BLM devices type, the fault name is "Ix",
            # where x is the integration channel
            integration_channel = 0
            integration_channel = int(fault_name.split('_')[0][-1])

            if integration_channel not in list(range(4)):
                raise ValueError("Function \"__get_fault_index(device_type_name={}, fault_name={}, channel_number={})\".\
                                Integration channel = {} out of range [0:3]".format(device_type_name, fault_name,
                                    channel_number, integration_channel))

            return "{}{}".format(channel_number, integration_channel)
        else:
            # For other application, the get index from the following 2-D dict
            bpm_fault_index = { "X":"0", "Y":"1", "CHRG":"2" }
            bcm_fault_index = { "CHARGE":"0", "DIFF": "1" }
            fault_indexes = {   "BPMS":bpm_fault_index,
                                "FARC":bcm_fault_index,
                                "TORO":bcm_fault_index }
            return fault_indexes[device_type_name][fault_name]

    def get_analog_type_name(self, device_type_name):
        """
        Return the fourth PV field for the analog measument type 
        according to the device type:
          * SOLN, BEND => CURRENT
          * PBLM, LBLM, CBLM => LOSS
          * TORO, FARC => CHARGE
        """
        if device_type_name in ["SOLN", "BEND", "KICK"]:
            return "BACT"
        elif device_type_name in ["PBLM", "LBLM", "CBLM", "BLM"]:
            return "LOSS"
        elif device_type_name in ["TORO", "FARC"]:
            return "CHARGE"
        elif device_type_name in ['BPMS']:
            return ""
        elif device_type_name in ['BLEN']:
            return ""
        else:
            raise ValueError("Function \"get_analog_type_name(device_type_name={})\". Invalid device type name"
                             .format(device_type_name))

    def get_app_type_name(self, device_type_name):
        """
        Get the app type name used in the EPICS DB.
        The name is application specific as follows:
          * SOLN, BEND, PBLM, LBLM, BLM => BLM
          * BPMS       => BPM
          * TORO, FARC => BCM
        """

        if device_type_name in ["SOLN", "BEND", "PBLM", "CBLM", "LBLM", "BLEN", "BLM", "KICK"]:
            # Solenoids uses the same HW/SW as beam loss monitors
            return "BLM"
        elif device_type_name == "BPMS":
            return "BPM"
        elif device_type_name in ["FARC", "TORO"]:
            # Both Toroids and Faraday cups use the BCM HW/SW
            return "BCM"
        else:
            raise ValueError("Function \"get_app_name(device_type_id={})\". Invalid device type name"
                .format(device_type_name))

    def __get_digital_channel(self, mps_db_session, channel_id):
        """
        Return the digital channel which id correspond to the passed channel_id.
        """
        digital_channel = mps_db_session.query(models.DigitalChannel).filter(models.DigitalChannel.id==channel_id).all()

        number_channles = len(digital_channel)
        if number_channles == 1:
            return digital_channel[0]
        elif number_channles == 0:
            raise ValueError("Function \"__get_digital_channel(channel_id={}\"). Not channel was found".format(channel_id))
        else:
            raise ValueError("Function \"__get_digital_channel(channel_id={}\"). More than one channel matched.".format(channel_id))

    def __get_bay_ch_number(self, mps_db_session, channel_id, type_id):
        """
        Return the bay, channel number corresponding to the analog channel and the channel number (from 0 to 5)
        with id = channel_id of of type id = type_id
        """
        analog_channel = mps_db_session.query(models.AnalogChannel).filter(models.AnalogChannel.id==channel_id).all()

        number_channels = len(analog_channel)

        if (number_channels == 0):
            raise ValueError("Function \"__get_bay_ch_number(channel_id={})\". Not analog channel was found.".format(channel_id))
        elif (number_channels > 1):
            raise ValueError("Function \"__get_bay_ch_number(channel_id={})\". More than one analog channel matches.".format(channel_id))

        # Check if this is AMC generic ADC/DAC card. These card have 'number' = 2 in table 'application_card_type'.
        if (type_id == 2):
            # For these cards, channel.numbers [0:2] are in bay 0, channel [0:2];
            # and channal.numbers [3:5] are in bay 1, channel [0:2]
            return analog_channel[0].number // 3, analog_channel[0].number % 3, analog_channel[0].number
        else:
            # For other cards the channel number is the bay number, and the channel is 0
            return analog_channel[0].number, 0, analog_channel[0].number

    def __get_fault(self, mps_db_session, fault_id):
        """
        Return the fault which id correspond to the passed fault_id.
        """
        fault = mps_db_session.query(models.Fault).filter(models.Fault.id==fault_id).all()

        if len(fault) == 1:
            return fault[0]
        elif len(fault) == 0:
            raise ValueError("Function \"__get_fault(fault_id={}). Not fault was found.\""
                .format(fault_id))
        else:
            raise ValueError("Function \"__get_fault(fault_id={}). More than one fault matches\""
                .format(fault_id))

    def __get_device_type_name(self, mps_db_session, device_type_id):
        """
        Return the device type name corresponding to the passed device_type_id.
        """
        device_type = mps_db_session.query(models.DeviceType).filter(models.DeviceType.id==device_type_id).all()

        if len(device_type) == 1:
            return device_type[0].name
        elif len(device_type) == 0:
            raise ValueError("Function \"__get_device_type_name(device_type_id={}). Not fault was found.\""
                .format(device_type_id))
        else:
            raise ValueError("Function \"__get_device_type_name(device_type_id={}). More than one device matches.\""
                .format(device_type_id))
