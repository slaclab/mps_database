#!/usr/bin/env python

from mps_config import MPSConfig, models
from mps_names import MpsName
from sqlalchemy import func, exc
import argparse
import os
import errno
import re
import shutil

def create_dir(path, clean=False, debug=False):
    """
    Create a new directory into a specified path.

    If the directory already exists and the 'clean' flag is true,
    then the directory will be removed, and then recreated; otherwise
    the directory will not be created.

    If 'debug' is true, them debug messages with information will be
    displayed.
    """
    dir_name = os.path.dirname(path)
    dir_exist = os.path.exists(dir_name)

    if clean and dir_exist:
        if debug:
            print("Directory '{}' exists. Removing it...".format(dir_name))

        shutil.rmtree(dir_name, ignore_errors=True)
        dir_exist = False


    if not dir_exist:
        if debug:
            print("Directory '{}' does not exist. Creating it...".format(dir_name))

        try:
            os.makedirs(dir_name)

            if debug:
                print("Directory created.")

        except OSError as exc: # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise

def format_path(path):
    """
    (str) -> str
    Make sure that path ends with a backslash '/'
    """
    return path if path.endswith('/') else path + '/'

class MpsDbReader:
    """
    This class is used to open a session to the MPS Database,
    making sure that the it is properly closed at the end.

    It is intended to be called in a 'with-as' code block.
    """
    def __init__(self, db_file):
        print("Creating DB reader object with '{}'".format(db_file))
        self.db_file = db_file

    def __enter__(self):
        # Open the MPS database
        print("Opening MPS Db session")
        self.mps_db = MPSConfig(self.db_file)

        # Return a session to the database
        return self.mps_db.session

    def __exit__(self, exc_type, exc_value, traceback):
        print("Closing MPS Db session")

        # Close the MPS database
        self.mps_db.session.close()


class MpsAppReader:
    """
    This class extract all the necessary information of each application
    defined in the MPS database, necessary to generate EPICS Databases,
    configuration files, and GUI screens.
    """
    def __init__(self, db_file, template_path, dest_path, app_id, verbose):

        self.template_path = template_path
        self.dest_path = dest_path
        self.verbose = verbose
        self.app_id = app_id

        # This is the list of all applications
        self.analog_apps = []
        self.digital_apps= []
        
        # List of Link Nodes by cpu_name + slot - track if it has only digital, analog or both apps
        self.link_nodes = {}

        # Open a session to the MPS database
        with MpsDbReader(db_file) as mps_db_session:

            # Extract the application information
            self.__extract_apps(mps_db_session)
            self.mps_name = MpsName(mps_db_session)

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

        Each device in the application devices list will be a dictionary with
        the following structure:
        - type_name (str)
        - bay_number (number)
        - area (str)
        - position (str)
        - faults (dict)

        The device faults dictionary will be have keys equal to the fault ID, and the
        values will be dictionary with the following structure:
        - name (str)
        - description (str)
        - bit_positions (list)

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
        - devices (list)

        Each device in the application devices list will be a dictionary with
        the following structure:
        - type_name (str)
        - area (str)
        - position (str)
        - inputs (list)

        Each input in the device inputs list will be a dictionary with
        the following structure:
        - name (str)
        - bit_position (number)
        - zero_name (str)
        - one_name (str)
        - alarm_state (number)
        - debounce (number)
        """

        try:
            # Get all the apps defined in the database
            if (app_id == None):
                app_cards = mps_db_session.query(models.ApplicationCard).all()
            else:
                app_cards = mps_db_session.query(models.ApplicationCard).\
                    filter(models.ApplicationCard.global_id == app_id).all()
            link_nodes = mps_db_session.query(models.LinkNode).all()
        except exc.SQLAlchemyError as e:
            raise

        if (len(link_nodes) > 0):
            for ln in link_nodes:
                name = ln.get_name()
                self.link_nodes[name] = 'Unknown'

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

                # Get this application data
                app_data = {}
                app_data["app_id"] = app_card.global_id
                app_data["cpu_name"] = app_card.link_node.cpu
                app_data["crate_id"] = app_card.crate.crate_id
                app_data["slot_number"] = app_card.slot_number
                app_data["link_node_name"] = ln_name
                app_data["link_node_area"] = app_card.link_node.area
                app_data["link_node_location"] = app_card.link_node.location
                app_data["card_index"] = self.__get_card_id(app_card.slot_number, app_card.type_id)
                app_data["lc1_node_id"] = str(app_card.link_node.lcls1_id)

                if (ln_name in self.link_nodes):
                    if (self.link_nodes[ln_name] == 'Unknown'):
                        self.link_nodes[ln_name] = 'Analog'
                    else:
                        self.link_nodes[ln_name] = 'Mixed'

                # Defines whether the IOC_NAME env var should be added no the mps.env
                # file. In order to add only once we need to figure out if there are
                # other cards with the same SIOC. If there is a digital card the SIOC
                # is written in the digital section. If a card is a "Generic ADC" and
                # it is not in slot 2 then it has its own SIOC (there are only ~7 cases
                # like that)
                app_data["analog_link_node"] = False
                if (app_card.link_node.slot_number != 2 and app_card.name == "Generic ADC"):
                    app_data["analog_link_node"] = True # Non-slot 2 link node
                elif (app_card.link_node.slot_number == 2):
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
                        device_data["bay_number"], device_data["channel_number"] = self.__get_bay_ch_number(mps_db_session, device.channel_id, app_card.type_id)
                        device_data["area"] = device.area
                        device_data["position"] = device.position
                        device_data["faults"] = {}

                        # Iterate over all the faults in this device
                        for fault_input in fault_inputs:
                            faults = mps_db_session.query(models.Fault).filter(models.Fault.id==fault_input.fault_id).all()
                            if (len(faults) != 1):
                                print 'ERROR: Fault not defined'
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
                                for fs in fault_states:
                                    fault_data["bit_positions"].append(fs.device_state.get_bit_position())
 
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

                # Get this application data
                app_data = {}
                app_data["app_id"] = app_card.global_id
                app_data["cpu_name"] = app_card.link_node.cpu
                app_data["crate_id"] = app_card.crate.crate_id
                app_data["slot_number"] = app_card.slot_number
                app_data["link_node_area"] = app_card.link_node.area
                app_data["link_node_name"] = ln_name
                app_data["link_node_location"] = app_card.link_node.location
                app_data["card_index"] = self.__get_card_id(app_card.slot_number, app_card.type_id)
                app_data["virtual"] = False
                app_data["lc1_node_id"] = str(app_card.link_node.lcls1_id)
                app_data["devices"] = []
                if (app_card.has_virtual_channels()):
                    app_data["virtual"] = true

                if (ln_name in self.link_nodes):
                    if (self.link_nodes[ln_name] == 'Unknown'):
                        self.link_nodes[ln_name] = 'Digital'
                    else:
                        self.link_nodes[ln_name] = 'Mixed'

                # Iterate over all the analog devices in this application
                for device in digital_devices:

                    # Look for all the inputs in this device
                    inputs = device.inputs

                    # Check if this device has inputs. Only devices with inputs defined will be included
                    if len(inputs):

                        # get this device data
                        device_data = {}
                        device_data["type_name"] = self.__get_device_type_name(mps_db_session, device.device_type_id)
                        device_data["area"] = device.area
                        device_data["position"] = device.position
                        device_data["inputs"] = []

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
                                input_data["alarm_state"] = digital_channel.alarm_state
                                if (digital_channel.alarm_state == 0):
                                    input_data["zero_severity"] = "MAJOR"
                                    input_data["one_severity"] = "NO_ALARM"
                                else:
                                    input_data["zero_severity"] = "NO_ALARM"
                                    input_data["one_severity"] = "MAJOR"

                            # Add this input to the list of inputs of the current device
                            device_data["inputs"].append(input_data)

                        # Add this device to the list of devices of the current application
                        app_data["devices"].append(device_data)


                # Add this application to the list of applications, if its list of devices is not empty
                # The list of devices will be empty if not device in this app have defined fault inputs,
                # as devices without faults inputs won't be processed.
                if app_data["devices"]:
                    self.digital_apps.append(app_data)

    def generate_epics_db(self):
        """
        Generate the EPICS database and configuration files from the application data obtained by the
        extract_apps method.

        The files will be written in the destination directory specified from the user (TOP),
        following the following structure:

        <TOP>/app_db/<cpu_name>/<crate_id>/<slot_number>/

        Using the <cpu_name>, <crate_id>, and <slot_number> defined in each application.

        """
        print("==================================================")
        print("== Generating EPICS DB and configuration files: ==")
        print("==================================================")
            
        if (self.verbose):
        # Generate digital application related databases and configuration files
            print("----------------------------")
            print("--  Digital applications  --")
            print("----------------------------")
        for app in self.digital_apps:
            app_path = '{}app_db/{}/{:04X}/{:02}/'.format(self.dest_path, app["cpu_name"], app["crate_id"], app["slot_number"])
            app_prefix = 'MPLN:{}:{}:{}'.format(app["link_node_area"].upper(), app["link_node_location"].upper(), app["card_index"])

            if (self.verbose):
                print("Application path   : {}".format(app_path))
                print("Application prefix : {}".format(app_prefix))

            if (app["link_node_name"] in self.link_nodes):
                if (self.link_nodes[app["link_node_name"]] == 'Digital' or 
                    self.link_nodes[app["link_node_name"]] == 'Mixed'):
                    self.__write_mps_db(path=app_path, macros={"P":app_prefix})
                elif (self.link_nodes[app["link_node_name"]] == 'Unknown'):
                    print('ERROR: no app defined for link node {}'.format(app["link_node_name"]))
                    exit(2)

            self.__write_dig_app_id_confg(path=app_path, macros={"ID":str(app["app_id"])})

            # Add the IOC name environmental variable for the Link Nodes
            self.__write_header_env(path=app_path, macros={})
            self.__write_iocinfo_env(path=app_path, macros={"AREA":app["link_node_area"].upper(),
                                                            "LOCATION":app["link_node_location"].upper(),
                                                            "LOCATION_INDEX":"0{}".format(5),
                                                            "CARD_INDEX":str(app["card_index"]),
                                                            "APP_ID":str(app["app_id"])})
            self.__write_app_id_env(path=app_path, macros={"APP_TYPE":"MPS_DIG_APP",
                                                           "APP_ID_NAME":"MPS_DIG_APP_ID",
                                                           "APP_ID":str(app["app_id"])})
            self.__write_lc1_id_env(path=app_path, macros={"NODE_ID":app["lc1_node_id"]})

            for device in app["devices"]:
                device_prefix = "{}:{}:{}".format(device["type_name"], device["area"], device["position"])

                if (self.verbose):
                    print("  Device prefix : {}".format(device_prefix))

                for input in device["inputs"]:

                    if app["virtual"]:
                        if (input["bit_position"]>=32):
                            print("Virtual Input: {}, number={}".format(input["name"], input["bit_position"]))
                            vmacros = {  "P":device_prefix,
                                         "R":input["name"],
                                         "N":self.mps_name.getDeviceInputNameFromId(input["db_id"]),
                                         "INPV":input["input_pv"],
                                         "ALSTATE":str(input["alarm_state"]),
                                         "NALSTATE":str(not input["alarm_state"]),
                                         "ZSV":input["zero_severity"],
                                         "OSV":input["one_severity"],
                                         "BIT":str(input["bit_position"]),
                                         "ZNAM":input["zero_name"],
                                         "ONAM":input["one_name"] }
                            self.__write_virtual_db(path=app_path, macros=vmacros)


                    macros = {  "P":device_prefix,
                                "R":input["name"],
                                "BIT":input["bit_position"],
                                "ZNAM":input["zero_name"],
                                "ONAM":input["one_name"] }

                    if (self.verbose):
                        print("    Digital Input : {}".format(input["name"]))
                    #self.write_thr_base_db(path=app_path, macros=macros)
        if (self.verbose):
            print("----------------------------")

            print("==================================================")
            print("")

        # Generates analog application related databases and configuration files
        if (self.verbose):
            print("--------------------------")
            print("--  Analog applications --")
            print("--------------------------")
        for app in self.analog_apps:
            app_path = '{}app_db/{}/{:04X}/{:02}/'.format(self.dest_path, app["cpu_name"], app["crate_id"], app["slot_number"])
            app_prefix = 'MPLN:{}:{}:{}'.format(app["link_node_area"].upper(), app["link_node_location"].upper(), app["card_index"])

            if (self.verbose):
                print("Application path   : {}".format(app_path))
                print("Application prefix : {}".format(app_prefix))

            if (app["link_node_name"] in self.link_nodes):
                if (self.link_nodes[app["link_node_name"]] == 'Analog'):
                    self.__write_mps_db(path=app_path, macros={"P":app_prefix})
                elif (self.link_nodes[app["link_node_name"]] == 'Unknown'):
                    print('ERROR: no app defined for link node {}'.format(app["link_node_name"]))
                    exit(2)

            self.__write_app_id_config(path=app_path, macros={"ID":str(app["app_id"])})
            self.__write_thresholds_off_config(path=app_path)
            self.__write_prefix_env(path=app_path, macros={"P":app_prefix})

            # Add the IOC name environmental variable for the Link Nodes
            if app["analog_link_node"]:
                self.__write_header_env(path=app_path, macros={})
                self.__write_iocinfo_env(path=app_path, macros={"AREA":app["link_node_area"].upper(),
                                                                "LOCATION":app["link_node_location"].upper(),
                                                                "LOCATION_INDEX":"0{}".format(5),
                                                                "CARD_INDEX":str(app["card_index"])})
                self.__write_lc1_id_env(path=app_path, macros={"NODE_ID":app["lc1_node_id"]})

            self.__write_app_id_env(path=app_path, macros={"APP_TYPE":"MPS_ANA_APP",
                                                           "APP_ID_NAME":"MPS_ANA_APP_ID",
                                                           "APP_ID":str(app["app_id"])})

            for device in app["devices"]:
                device_prefix = "{}:{}:{}".format(device["type_name"], device["area"], device["position"])

                if (self.verbose):
                    print("  Device prefix : {}".format(device_prefix))

                for fault in device["faults"].values():

                    macros = {  "P":device_prefix,
                                "BAY":str(device["bay_number"]),
                                "APP":self.__get_app_type_name(device["type_name"]),
                                "FAULT":fault["name"],
                                "FAULT_INDEX":self.__get_fault_index(device["type_name"], fault["name"], device["channel_number"]),
                                "DESC":fault["description"],
                                "EGU":self.__get_app_units(device["type_name"],fault["name"]) }

                    self.__write_thr_base_db(path=app_path, macros=macros)


                    for bit in fault["bit_positions"]:
                        fault_prefix = "{}_T{}".format(fault["name"], bit)

                        if (self.verbose):
                            print("    Fault prefix : {}".format(fault_prefix))

                        macros["BIT_POSITION"] = str(bit)
                        self.__write_thr_db(path=app_path, macros=macros)

                    macros = { "BAY_INP_NAME_MACRO": 'BAY{}_INP{}'.format(str(device["bay_number"]),
                                                                          str(device["channel_number"])),
                               "BAY_INP_NAME_DEFINE": "",
                               "BAY_DB_FILE_MACRO": 'BAY{}_DB_FILE'.format(str(device["bay_number"])),
                               "BAY_DB_FILE": 'db/mps_blm.db',
                               "BAY_INP_NAME_MACRO": 'BAY{}_INP{}_NAME'.format(str(device["bay_number"]),
                                                                          str(device["channel_number"])),
                               "BAY_INP_NAME": device_prefix}
                    self.__write_analog_input_env(path=app_path, macros=macros)
#                    epicsEnvSet("$(BAY_INP_NAME_MACRO)", "$(BAY_INP_NAME_DEFINE)")
#                    epicsEnvSet("$(BAY_DB_FILE_MACRO)", "$(BAY_DB_FILE)")
#                    epicsEnvSet("$(BAY_INP_NAME_MACRO)", "$(BAY_INP_NAME)")


        if (self.verbose):
            print("--------------------------")


    def print_app_data(self):
        """
        Print the content of the application data obtained by the extract_apps method.
        """
        print("===================================")
        print("==            REULTS:            ==")
        print("===================================")

        # Analog application results
        print("--------------------------")
        print("--  Analog applications --")
        print("--------------------------")
        print("Number of analog application processed: {}".format(len(self.analog_apps)))
        if (self.verbose):
            for app in self.analog_apps:
                print("  Application data:")
                print("  - - - - - - - - - - - - -")
                print('  - EPICS PREFIX: MPLN:{}:{}:{}'.format(app["link_node_area"].upper(), app["link_node_location"].upper(), app["card_index"]))
                print("  - App ID             : {}".format(app["app_id"]))
                print("  - Cpu name           : {}".format(app["cpu_name"]))
                print("  - Crate ID           : {}".format(app["crate_id"]))
                print("  - Slot number        : {}".format(app["slot_number"]))
                print("  - Link node area     : {}".format(app["link_node_area"]))
                print("  - Link node location : {}".format(app["link_node_location"]))
                print("  - Card index         : {}".format(app["card_index"]))
                print("  - Number of devices  : {}".format(len(app["devices"])))
                for device in app["devices"]:
                    print("    Device data:")
                    print("    .....................")
                    print("      - EPICS PREFIX: {}:{}:{}".format(device["type_name"], device["area"], device["position"]))
                    print("      - Type name        : {}".format(device["type_name"]))
                    print("      - Bay number       : {}".format(device["bay_number"]))
                    print("      - Channel number   : {}".format(device["channel_number"]))
                    print("      - Area             : {}".format(device["area"]))
                    print("      - Position         : {}".format(device["position"]))
                    print("      - Number of faults : {}".format(len(device["faults"])))
                    for fault_id,fault_data in device["faults"].items():
                        print("      Fault data:")
                        print("      . . . . . . . . . . . . ")
                        print("        - EPICS PREFIX: {}_T{}".format(fault_data["name"], fault_data["bit_positions"][0]))
                        print("        - ID            : {}".format(fault_id))
                        print("        - Name          : {}".format(fault_data["name"]))
                        print("        - Description   : {}".format(fault_data["description"]))
                        print("        - Bit positions : {}".format(fault_data["bit_positions"]))
                        print("      . . . . . . . . . . . . ")
                    print("    .....................")
                print("  - - - - - - - - - - - - -")
                print("")
            print("--------------------------")

        # Digital application result
        print("----------------------------")
        print("--  Digital applications  --")
        print("----------------------------")
        print("Number of digital application processed: {}".format(len(self.digital_apps)))
        if (self.verbose):
            for app in self.digital_apps:
                print("  Application data:")
                print("  - - - - - - - - - - - - -")
                print('  - EPICS PREFIX: MPLN:{}:{}:{}'.format(app["link_node_area"].upper(), app["link_node_location"].upper(), app["card_index"]))
                print("  - App ID             : {}".format(app["app_id"]))
                print("  - Cpu name           : {}".format(app["cpu_name"]))
                print("  - Crate ID           : {}".format(app["crate_id"]))
                print("  - Slot number        : {}".format(app["slot_number"]))
                print("  - Link node area     : {}".format(app["link_node_area"]))
                print("  - Link node location : {}".format(app["link_node_location"]))
                print("  - Card index         : {}".format(app["card_index"]))
                print("  - Number of devices  : {}".format(len(app["devices"])))
                for device in app["devices"]:
                    print("    Device data:")
                    print("    .....................")
                    print("      - EPICS PREFIX: {}:{}:{}".format(device["type_name"], device["area"], device["position"]))
                    print("      - Type name        : {}".format(device["type_name"]))
                    print("      - Area             : {}".format(device["area"]))
                    print("      - Position         : {}".format(device["position"]))
                    print("      - Number of inputs : {}".format(len(device["inputs"])))
                    for input in device["inputs"]:
                        print("      Input data:")
                        print("      . . . . . . . . . . . . ")
                        print("        - EPICS PREFIX: {}".format(input["name"]))
                        print("        - Name         : {}".format(input["name"]))
                        print("        - Bit position : {}".format(input["bit_position"]))
                        print("        - Zero name    : {}".format(input["zero_name"]))
                        print("        - One name     : {}".format(input["one_name"]))
                        print("        - Alarm state  : {}".format(input["alarm_state"]))
                        print("        - Debounce     : {}".format(input["debounce"]))
                        print("      . . . . . . . . . . . . ")
                    print("    .....................")
                print("  - - - - - - - - - - - - -")
                print("")
            print("----------------------------")


        print("===================================")

        for k,v in self.link_nodes.items():
            print '{}: {}'.format(k, v)


    def __get_card_id(self, slot_number, type_id):
        """
        Generate the card ID based on the application
        slot number and type id.

        If the application is a Link Nodes (slot # 2) then
        the card number will be:
        - 1 for analog cards (type id: 2)
        - 2 for digital cards (type id: 1)
        - 3 for virtual cards (type id: 6)

        For other applications, the card number will be
        the slot number + 1.
        """
        if slot_number == 2:
            if type_id == 1:
                return 2
            elif type_id == 2:
                return 1
            elif type_id == 6:
                return 3
            else:
                raise ValueError("Function \"get_card_id(slot_number={}, type_id={})\". Invalid type_id for a Link Node"
                    .format(slot_number, type_id))
        else:
            return slot_number + 1

    def __get_app_type_name(self, device_type_name):
        """
        Get the app type name used in the EPICS DB.
        The name is application specific as follows:
          * SOLN, BEND, PBLM, LBLM, BLM => BLM
          * BPMS       => BPM
          * TORO, FARC => BCM
        """

        if device_type_name in ["SOLN", "BEND", "PBLM", "BLM", "LBLM", "BLEN"]:
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


    def __get_app_units(self, device_type_name, fault_name):
        """
        Get the application enginering units used in the EPICS DB.
        The unit is application and fault specific as follows:
          * SOLN, BEND, PBLM, LBLM, BLM, BLEN => uA
          * BPMS
            - X, Y     => mm
            - TMIT     => Nel
          * TORO, FARC => Nel
        """

        if device_type_name in ["SOLN", "BEND", "PBLM", "BLM", "LBLM", "BLEN"]:
            # Solenoid devices use 'uA'.
            return "uA"
        elif device_type_name == "BPMS":
            # For BPM, the units depend on the type of fault
            if fault_name in ["X", "Y"]:
                # Fault X, Y use 'mm'
                return "mm"
            elif fault_name == "TMIT":
                # TIMIT uses 'Nel'
                return "Nel"
            else:
                raise ValueError("Function \"__get_app_units(device_type_name={}, fault_name={})\". Invalid fault name"
                    .format(device_type_name, fault_name))

        elif device_type_name in ["FARC", "TORO"]:
            # BCM devices use 'Nel'
            return "Nel"
        else:
            raise ValueError("Function \"__get_app_units(device_type_name={}, fault_name={})\". Invalid device type name"
                    .format(device_type_name, fault_name))

    def __get_fault_index(self, device_type_name, fault_name, channel_number):
        """
        Get the 'fault_index' used in the EPICS DB.
        The fault index is appication specific as follows:
          * SOLN, BEND, PBLM, LBLM, BLM => (X)(Y), X=input channel(0-2), Y=Integration channel (0-3)
          * BPM     => (X),    X=Channel (0:X, 1:Y, 2, TIMIT)
          * TORO,FC => (X),    X=Channel (0:Charge, 1:Difference)
          * BLEN    => 0
        """
        if device_type_name in ["SOLN", "BEND", "PBLM", "BLM", "LBLM", "BLEN"]:
            # For SOLN devices type, the fault name is "Ix",
            # where x is the integration channel
            integration_channel = int(fault_name[-1])

            if integration_channel not in range(4):
                raise ValueError("Function \"__get_fault_index(device_type_name={}, fault_name={}, channel_number={})\".\
                                Integration channel = {} out of range [0:3]".format(device_type_name, fault_name,
                                    channel_number, integration_channel))

            return "{}{}".format(channel_number, integration_channel)
        else:
            # For other application, the get index from the following 2-D dict
            bpm_fault_index = { "X":"0", "Y":"1", "TMIT":"2" }
            bcm_fault_index = { "CHARGE":"0", "DIFF": "1" }
            fault_indexes = {   "BPMS":bpm_fault_index,
                                "FARC":bcm_fault_index,
                                "TORO":bcm_fault_index }
            return fault_indexes[device_type_name][fault_name]

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
        Return the bay and channel number corresponding to the analog channel
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
            return analog_channel[0].number // 3, analog_channel[0].number % 3
        else:
            # For other cards the channel number is the bay number, and the channel is 0
            return analog_channel[0].number, 0

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

    def __write_app_id_config(self, path, macros):
        """
        Write the appID configuration section to the application configuration file.

        This configuration will be load by all applications.
        """
        self.__write_fw_config(path=path, template_name="app_id.template", macros=macros)

    def __write_dig_app_id_confg(self, path, macros):
        """
        Write the digital appID configuration section to the application configuration file.

        This configuration will be load by all link nodes.
        """
        self.__write_fw_config(path=path, template_name="dig_app_id.template", macros=macros)

    def __write_thresholds_off_config(self, path):
        """
        Write the Threshold off configuration section to the application configuration file.

        This configuration will be load by all applications.
        """
        self.__write_fw_config(path=path, template_name="thresholds_off.template", macros={})

    def __write_mps_db(self, path, macros):
        """
        Write the base mps records to the application EPICS database file.

        These records will be loaded once per each device.
        """
        self.__write_epics_db(path=path, template_name="mps.template", macros=macros)

    def __write_virtual_db(self, path, macros):
        """
        Write records for digital virtual inputs
        """
        self.__write_epics_db(path=path, template_name="virtual.template", macros=macros)

    def __write_thr_base_db(self, path, macros):
        """
        Write the base threshold record to the application EPICS database file.

        These records will be loaded once per each fault.
        """
        self.__write_epics_db(path=path, template_name="thr_base.template", macros=macros)

    def __write_thr_db(self, path, macros):
        """
        Write the threshold records to the application EPICS database file.

        These records will be load once per each bit in each fault.
        """
        self.__write_epics_db(path=path, template_name="thr.template", macros=macros)

    def __write_analog_input_env(self, path, macros):
        """
        Write the macros for loading analog input records

        This environmental variable will be loaded by all analog applications
        """
        self.__write_epics_env(path=path, template_name="analog_inputs.template", macros=macros)

    def __write_app_id_env(self, path, macros):
        """
        Write the appID to the environmental variable file.

        This environmental variable will be loaded by all applications.
        """
        self.__write_epics_env(path=path, template_name="app_id.template", macros=macros)

    def __write_header_env(self, path, macros):
        """
        Write the header for the MPS file containing environmental variables.

        This environmental variable will be loaded by all applications.
        """
        self.__write_epics_env(path=path, template_name="header.template", macros=macros)

    def __write_prefix_env(self, path, macros):
        """
        Write the  mps PV name prefix environmental variable file.

        This environmental variable will be loaded by all applications.
        """
        self.__write_epics_env(path=path, template_name="prefix.template", macros=macros)

    def __write_iocinfo_env(self, path, macros):
        """
        Write the LN IOC related environmental variable file.

        This environmental variable will be loaded by all link nodes.
        """
        self.__write_epics_env(path=path, template_name="ioc_info.template", macros=macros)

    def __write_lc1_id_env(self, path, macros):
        """
        Write the LN LCLS-I node ID (used to assemble the LN IP address)

        This environmental variable will be loaded by all LCLS-I connected link nodes.
        """
        self.__write_epics_env(path=path, template_name="lc1_node_id.template", macros=macros)

    def __write_epics_db(self, path, template_name, macros):
        """
        Write the EPICS DB file into the 'path' directory.

        The resulting file is named "mps.db". Calling this function
        multiple times, will append the results into the same file.

        The file is created from the template file located in the directory
        "epics_db" inside the global template directory, substituting the
        macros definitions.
        """
        file = "{}mps.db".format(path)
        template = "{}epics_db/{}".format(self.template_path, template_name)
        self.__write_file_from_template(file=file, template=template, macros=macros)

    def __write_epics_env(self, path, template_name, macros):
        """
        Write the EPICS ENV file into the 'path' directory.

        The resulting file is named "mps.env". Calling this function
        multiple times, will append the results into the same file.

        The file is created from the template file located in the directory
        "epics_env" inside the global template directory, substituting the
        macros definitions.
        """
        file = "{}mps.env".format(path)
        template = "{}epics_env/{}".format(self.template_path, template_name)
        self.__write_file_from_template(file=file, template=template, macros=macros)

    def __write_fw_config(self, path, template_name, macros):
        """
        Write the FW configuration file into the 'path' directory.

        The resulting file is named "config.yaml". Calling this function
        multiple times, will append the results into the same file.

        The file is created from the tamplte file located in the directory
        "fw_config" inside the global template directory, substituting the
        macros definitions.
        """
        file = "{}config.yaml".format(path)
        template = "{}fw_config/{}".format(self.template_path, template_name)
        self.__write_file_from_template(file=file, template=template, macros=macros)

    def __write_file_from_template(self, file, template, macros):
        """
        Genetic method to write a file from a template, substituting the
        passed macro definitions.

        The output file is opened in append mode, so calling this function
        pointing to the same file will add content to the file.

        If the directory of the output file does not exist, it will be created.
        """
        create_dir(file)
        with open(file, 'a') as db, open(template, 'r') as template:
            for line in template:
                #print("*** {}".format(line))
                db.write(self.__expand_macros(line, macros))

    def __expand_macros(self, text, macros):
        """
        Generic method to substitute macros in a block of text.

        The macros are defined in a dictionary, where the keys are the macro
        and the value is the string to substitute it. The macros in the text
        and defined as $(MACRO_NAME), where only MACRO_NAME is the key string
        in the dictionary.

        It will return the original text will all the macros found in it
        substituted by the respective values.
        """
#        print macros.items()
        for k, v in macros.items():
            text = re.sub(r'\$\(({key}|{key},[^)]*)\)'.format(key=k),v, text)

        return text

#################
### Main Body ###
#################

def main(db_file, dest_path, template_path=None, app_id=None, verbose=False):

    if (template_path==None):
        template_path='templates/'

    # Generate the Mps application reader object
    mps_app_reader = MpsAppReader(db_file, template_path, dest_path, app_id, verbose)

    # Print a report of the found applications
    mps_app_reader.print_app_data()

    # Generated the application output file
    mps_app_reader.generate_epics_db()

if __name__ == "__main__":

    # Parse input arguments
    parser = argparse.ArgumentParser(description='Export Link Node EPICS databases')
    parser.add_argument('--db', metavar='database', required=True,
                        help='MPS SQLite database file')
    parser.add_argument('--dest', metavar='destination', required=True,
                        help='Destination location of the resulting EPICS database')
    # parser.add_argument('--template', default='templates/',
    #                     help='Path to EPICS DB template files')
    parser.add_argument('--template', required=False,
                        help='Path to EPICS DB template files')
    parser.add_argument('-v', action='store_true', default=False,
                        dest='verbose', help='Verbose output')
    parser.add_argument('--app-id', type=int, help='Generate database only for this app')

    args = parser.parse_args()

    db_file = args.db
    template_path = args.template
    dest_path = args.dest
    verbose = args.verbose
    app_id = args.app_id
    clean = True
    if app_id != None:
        print ('Exporting databases for AppId={}'.format(app_id))
        clean = False

    # Check formatting of the destination path
    dest_path = format_path(dest_path)

    # Create a new clean output directory in the specified path
    create_dir(dest_path, clean=clean, debug=True)

    # If the template path is specified, check its format and if it exists
    if template_path:
        template_path = format_path(template_path)

        # Check is the template path exist
        if not os.path.exists(template_path):
            print("EPICS DB template directory '{}' not found.".format(template_path))
            exit(1)

    main(db_file=db_file, dest_path=dest_path, template_path=template_path, app_id = app_id, verbose=verbose)
