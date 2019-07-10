from mps_config import MPSConfig, models
from mps_names import MpsName
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
#    def __init__(self, db_file, template_path, dest_path, app_id, verbose):
    def __init__(self, db_file='', app_id=None, verbose=False):

        self.app_id = app_id 
        self.verbose = verbose

        # This is the list of all applications
        self.analog_apps = []
        self.digital_apps= []
        
        # List of Link Nodes by cpu_name + slot - track if it has only digital, analog or both apps
        self.link_nodes = {}

        self.config_version = os.path.basename(db_file).lstrip("mps_config-").rstrip(".db")

        # Open a session to the MPS database
        with MpsDbReader(db_file) as mps_db_session:

            # Extract the application information
            self.__extract_apps(mps_db_session)
            self.mps_name = MpsName(mps_db_session)

    def __add_slot_information(self, mps_db_session, ln_name, app_card):
        if app_card.slot_number in self.link_nodes[ln_name]['slots']:
            print('ERROR: Found multiple apps in same slot: link node {}, slot {}'.\
                      format(ln_name, app_card.slot_number))
            exit(1)
        
        slot_info = {}
        slot_info['pv_base'] = app_card.get_pv_name()

        try:
            app_type = mps_db_session.query(models.ApplicationType).\
                filter(models.ApplicationType.id == app_card.type_id).one()
        except exc.SQLAlchemyError as e:
            raise

        slot_info['type'] = app_type.name
        self.link_nodes[ln_name]['slots'][app_card.slot_number] = slot_info

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
            if (self.app_id == None):
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
                self.link_nodes[name] = {}
                self.link_nodes[name]['type'] = 'Unknown'
                self.link_nodes[name]['slots'] = {}

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
                app_data["card_index"] = app_card.get_card_id()
                app_data["lc1_node_id"] = str(app_card.link_node.lcls1_id)
                app_data["app_prefix"] = app_card.get_pv_name()

                self.__add_slot_information(mps_db_session, ln_name, app_card)

                if (ln_name in self.link_nodes):
                    if (self.link_nodes[ln_name]['type'] == 'Unknown' or
                        self.link_nodes[ln_name]['type'] == 'Analog'):
                        self.link_nodes[ln_name]['type'] = 'Analog'
                    else:
                        self.link_nodes[ln_name]['type'] = 'Mixed'

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
                elif (app_card.link_node.slot_number == 2):
                    self.link_nodes[ln_name]['analog_slot'] = 2
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
                        device_data["prefix"] = '{}:{}:{}'.format(device_data["type_name"], device.area, device.position)

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
                app_data["card_index"] = app_card.get_card_id()
                app_data["virtual"] = False
                app_data["lc1_node_id"] = str(app_card.link_node.lcls1_id)
                app_data["app_prefix"] = app_card.get_pv_name()
                app_data["devices"] = []
                if (app_card.has_virtual_channels()):
                    app_data["virtual"] = True

                if (ln_name in self.link_nodes):
                    if (self.link_nodes[ln_name]['type'] == 'Unknown'):
                        self.link_nodes[ln_name]['type'] = 'Digital'
                    else:
                        self.link_nodes[ln_name]['type'] = 'Mixed'

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
                        device_data["device_name"] = device.name
                        device_data["prefix"] = '{}:{}:{}'.format(device_data["type_name"], device.area, device.position)

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

    def pretty_print(self):
        pp=PrettyPrinter(indent=4)
        print('=== Digital Apps ===')
        pp.pprint(self.digital_apps)
        print('=== Analog Apps ===')
        pp.pprint(self.analog_apps)
        print('=== Link Nodes ===')
        pp.pprint(self.link_nodes)


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
                print("  - Link node name     : {}".format(app["link_node_name"]))
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
                print("  - Link node name     : {}".format(app["link_node_name"]))
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

        print('Found {} link nodes:'.format(len(self.link_nodes)))
        for k,v in self.link_nodes.items():
            print('{}: {}'.format(k, v['type']))

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
                fault_name = "TMIT"
            else:
                raise ValueError("Function \"get_app_name(device_type_name={}, channel_number={})\". Invalid channel number for BPMS device type"
                                 .format(device_type_name, channel_number))
            return self.__get_app_units(device_type_name, fault_name)
        else:
            return self.__get_app_units(device_type_name, "")

    def get_app_units(self, device_type_name, fault_name):
        """
        Get the application enginering units used in the EPICS DB.
        The unit is application and fault specific as follows:
          * SOLN, BEND, PBLM, LBLM, BLM, BLEN => uA
          * BPMS
            - X, Y     => mm
            - TMIT     => Nel
          * TORO, FARC => Nel
        """

        if device_type_name in ["SOLN", "BEND", "PBLM", "CBLM", "LBLM", "BLEN", "BLM"]:
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

    def get_fault_index(self, device_type_name, fault_name, channel_number):
        """
        Get the 'fault_index' used in the EPICS DB.
        The fault index is appication specific as follows:
          * SOLN, BEND, PBLM, LBLM, BLM => (X)(Y), X=input channel(0-2), Y=Integration channel (0-3)
          * BPM     => (X),    X=Channel (0:X, 1:Y, 2, TIMIT)
          * TORO,FC => (X),    X=Channel (0:Charge, 1:Difference)
          * BLEN    => 0
        """
        if device_type_name in ["SOLN", "BEND", "PBLM", "CBLM", "LBLM", "BLEN", "BLM"]:
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

    def get_analog_type_name(self, device_type_name):
        """
        Return the fourth PV field for the analog measument type 
        according to the device type:
          * SOLN, BEND => CURRENT
          * PBLM, LBLM, CBLM => LOSS
          * TORO, FARC => CHARGE
        """
        if device_type_name in ["SOLN", "BEND"]:
            return "CURRENT"
        elif device_type_name in ["PBLM", "LBLM", "CBLM", "BLM"]:
            return "LOSS"
        elif device_type_name in ["TORO", "FARC"]:
            return "CHARGE"
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

        if device_type_name in ["SOLN", "BEND", "PBLM", "CBLM", "LBLM", "BLEN", "BLM"]:
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
