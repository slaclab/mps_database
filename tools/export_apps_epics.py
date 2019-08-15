#!/usr/bin/env python

from mps_config import MPSConfig, models
from mps_names import MpsName
from sqlalchemy import func, exc
from mps_app_reader import MpsAppReader
import argparse
import os
import errno
import re
import shutil
import datetime
import ipaddress

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


class MpsAppExporter(MpsAppReader):
    """
    This class extract all the necessary information of each application
    defined in the MPS database, necessary to generate EPICS Databases,
    configuration files, and GUI screens.
    """
    def __init__(self, db_file, template_path, dest_path, app_id, manager_info, verbose):
        MpsAppReader.__init__(self, db_file=db_file, app_id=app_id, verbose=verbose)
        self.template_path = template_path
        self.dest_path = dest_path
        self.non_link_node_types = ["BPMS", "BLEN", "FARC", "TORO", "WIRE"]
        self.manager_info = manager_info

    def generate_epics_db(self):
        """
        Generate the EPICS database and configuration files from the application data obtained by the
        extract_apps method.

        The files will be written in the destination directory specified from the user (TOP),
        following the following structure:

        <TOP>/app_db/<cpu_name>/<crate_id>/<slot_number>/

        Using the <cpu_name>, <crate_id>, and <slot_number> defined in each application.

        """
        if (self.verbose):
        # Generate digital application related databases and configuration files
            print("==================================================")
            print("== Generating EPICS DB and configuration files: ==")
            print("==================================================")
            
            print("----------------------------")
            print("--  Digital applications  --")
            print("----------------------------")
        for app in self.digital_apps:
            app_path = '{}app_db/{}/{:04X}/{:02}/'.format(self.dest_path, app["cpu_name"], app["crate_id"], app["slot_number"])
            app_prefix = 'MPLN:{}:{}:{}'.format(app["link_node_area"].upper(), app["link_node_location"].upper(), app["card_index"])

            if (self.verbose):
                print("Application path   : {}".format(app_path))
                print("Application prefix : {}".format(app_prefix))
            
            self.__write_dig_app_id_confg(path=app_path, macros={"ID":str(app["app_id"])})

            # Add the IOC name environmental variable for the Link Nodes
            self.__write_header_env(path=app_path, macros={"MPS_LINK_NODE":app["link_node_name"],
                                                           "MPS_DB_VERSION":self.config_version,
                                                           "DATE":datetime.datetime.now().strftime('%Y.%m.%d-%H:%M:%S')})
            self.__write_iocinfo_env(path=app_path, macros={"AREA":app["link_node_area"].upper(),
                                                            "LOCATION":app["link_node_location"].upper()})
            if self.link_nodes[app["link_node_name"]]['type'] == 'Digital':
                self.__write_prefix_env(path=app_path, macros={"P":app_prefix})
                self.__write_mps_db(path=app_path, macros={"P":app_prefix, "THR_LOADED":"1"})
                self.__write_app_id_config(path=app_path, macros={"ID":"0"}) # If there are no analog cards, set ID to invalid

            has_virtual = False
            for device in app["devices"]:
                device_prefix = "{}:{}:{}".format(device["type_name"], device["area"], device["position"])

                if (self.verbose):
                    print("  Device prefix : {}".format(device_prefix))

                for input in device["inputs"]:

                    if app["virtual"]:
                        has_virtual = True
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

            self.__write_mps_db(path=app_path, macros={"P":app_prefix, "THR_LOADED":"0"})
            self.__write_app_id_config(path=app_path, macros={"ID":str(app["app_id"])})
            self.__write_thresholds_off_config(path=app_path)

            # Add the IOC name environmental variable for the Link Nodes
            if app["analog_link_node"]:
                self.__write_header_env(path=app_path, macros={"MPS_LINK_NODE":app["link_node_name"],
                                                               "MPS_DB_VERSION":self.config_version,
                                                               "DATE":datetime.datetime.now().strftime('%Y.%m.%d-%H:%M:%S')})

                self.__write_iocinfo_env(path=app_path, macros={"AREA":app["link_node_area"].upper(),
                                                                "LOCATION":app["link_node_location"].upper()})

            self.__write_prefix_env(path=app_path, macros={"P":app_prefix})

            spare_channels = range(0,6)
            for device in app["devices"]:
                device_prefix = "{}:{}:{}".format(device["type_name"], device["area"], device["position"])

                if (self.verbose):
                    print("  Device prefix : {}".format(device_prefix))

                if (device["type_name"] not in self.non_link_node_types):
                    macros = { "P":app_prefix,
                               "R":'ADC_DATA_{}'.format(device["channel_index"]),
                               "P_DEV":device_prefix,
                               "R_DEV":self.get_analog_type_name(device["type_name"])
                               }
                    self.__write_analog_db(path=app_path, macros=macros)

                    macros = { "P": app_prefix,
                               "CH":str(device["channel_index"]),
                               "CH_NAME":device["device_name"],
                               "CH_PVNAME":device_prefix,
                               "CH_SPARE":"0"
                               }
                    self.__write_link_node_channel_info_db(path=app_path, macros=macros)
                    spare_channels[device["channel_index"]] = -1

                    for fault in device["faults"].values():
                        macros = {  "P":device_prefix,
                                    "BAY":str(device["bay_number"]),
                                    "APP":self.get_app_type_name(device["type_name"]),
                                    "FAULT":fault["name"],
                                    "FAULT_INDEX":self.get_fault_index(device["type_name"], fault["name"], device["channel_number"]),
                                    "DESC":fault["description"],
                                    "EGU":self.get_app_units(device["type_name"],fault["name"])}

                        self.__write_thr_base_db(path=app_path, macros=macros)

                        # Generate PV for all possible thresholds, even if not defined in database
                        for bit in range(0,8):#fault["bit_positions"]:
                            fault_prefix = "{}_T{}".format(fault["name"], bit)
                            macros["BIT_POSITION"] = str(bit)
                            self.__write_thr_db(path=app_path, macros=macros)
                            if (self.verbose):
                                print("    Fault prefix : {}".format(fault_prefix))


            for ch in spare_channels:
                if ch > -1:
                    macros = { "P": app_prefix,
                               "CH":str(ch),
                               "CH_NAME":"Spare",
                               "CH_PVNAME":"None",
                               "CH_SPARE":"1"
                               }
                    self.__write_link_node_channel_info_db(path=app_path, macros=macros)

        #
        # Write db information about slots of each link node
        #
        for app in self.analog_apps + self.digital_apps:
            app_path = '{}app_db/{}/{:04X}/{:02}/'.format(self.dest_path, app["cpu_name"], app["crate_id"], app["slot_number"])
            link_node_info=self.link_nodes[app["link_node_name"]]
            if not 'exported' in link_node_info:
                for slot in range(2,8):
                    if slot in link_node_info['slots']:
                        macros = { "P": app["app_prefix"],
                                   "SLOT": str(slot),
                                   "SLOT_NAME": link_node_info['slots'][slot]['type'],
                                   "SLOT_PVNAME": link_node_info['slots'][slot]['pv_base'],
                                   "SLOT_SPARE": "0"}
                    else:
                        macros = { "P": app["app_prefix"],
                                   "SLOT": str(slot),
                                   "SLOT_NAME": "Spare",
                                   "SLOT_PVNAME": "Spare",
                                   "SLOT_SPARE": "1"}

                    self.__write_link_node_slot_info_db(path=app_path, macros=macros)

                # Add CH_* PVs for digital-only link nodes. These are added before 
                # only if the LN is Mixed or Analog
                if link_node_info['type'] == 'Digital':
                    for ch in spare_channels:
                        macros = { "P": app["app_prefix"],
                                   "CH":str(ch),
                                   "CH_NAME":"Not Available",
                                   "CH_PVNAME":"None",
                                   "CH_SPARE":"1"
                                   }
                        self.__write_link_node_channel_info_db(path=app_path, macros=macros)

                link_node_info['exported']=True

        #
        # Add Link Node related information
        #
        for ln_name,ln in self.link_nodes.items():
            self.__write_lc1_info_config(ln)
            self.__write_link_node_info_db(ln_name, ln)

        if (self.verbose):
            print("--------------------------")

    def __write_lc1_info_config(self, link_node):
        """
        Write the LCLS-I link node ID to the configuration file.
        """
        if link_node["lc1_node_id"] == "0":
            ip_str = u'192.168.0.0'.format(app["app_id"])
            print('ERROR: Found invalid link node ID (lcls1_id of 0)')
        else:
            ip_str = u'192.168.0.{}'.format(link_node["lc1_node_id"])

        ip_address = int(ipaddress.ip_address(ip_str))

        slot = 2
        if "analog_slot" in link_node: 
            slot = link_node["analog_slot"]
        path = '{}app_db/{}/{:04X}/{:02}/'.format(self.dest_path, link_node["cpu_name"], link_node["crate_id"], slot)

        mask = 0
        remap_dig = 0
        if link_node["type"] == "Digital":
            mask = 1
            remap_dig = link_node["dig_app_id"]

        bpm_index = 0
        blm_index = 0
        remap_bpm = [0, 0, 0, 0, 0]
        remap_blm = [0, 0, 0, 0, 0]
        for slot_number, slot_info in link_node["slots"].items():
            if slot_info["type"] == "BPM Card":
                if bpm_index < 5:
                    remap_bpm[bpm_index] = slot_info["app_id"]
                    mask |= 1 << (bpm_index + 1) # Skip first bit, which is for digital app
                    bpm_index += 1
                else:
                    print('ERROR: Cannot remap BPM app id {}, all remap slots are used already'.\
                              format(slot_info["app_id"]))
                          
            elif slot_info["type"] == "Generic ADC":
                if blm_index < 5:
                    remap_blm[blm_index] = slot_info["app_id"]
                    mask |= 1 << (blm_index + 1 + 5) # Skip first bit and 5 BPM bits
                    blm_index += 1
                else:
                    print('ERROR: Cannot remap BLM app id {}, all remap slots are used already'.\
                              format(slot_info["app_id"]))

        macros={"ID":str(link_node["lc1_node_id"]),
                "IP_ADDR":str(ip_address),
                "REMAP_DIG":str(remap_dig),
                "REMAP_BPM1":str(remap_bpm[0]),
                "REMAP_BPM2":str(remap_bpm[1]),
                "REMAP_BPM3":str(remap_bpm[2]),
                "REMAP_BPM4":str(remap_bpm[3]),
                "REMAP_BPM5":str(remap_bpm[4]),
                "REMAP_BLM1":str(remap_blm[0]),
                "REMAP_BLM2":str(remap_blm[1]),
                "REMAP_BLM3":str(remap_blm[2]),
                "REMAP_BLM4":str(remap_blm[3]),
                "REMAP_BLM5":str(remap_blm[4]),
                "REMAP_MASK":str(mask),
                }
        self.__write_fw_config(path=path, template_name="lc1_info.template", macros=macros)

    def __write_link_node_info_db(self, link_node_name, link_node):
        """
        Write the base mps records to the application EPICS database file.

        These records will be loaded once per each device.
        """
        slot = 2
        if "analog_slot" in link_node: 
            slot = link_node["analog_slot"]
        path = '{}app_db/{}/{:04X}/{:02}/'.format(self.dest_path, link_node["cpu_name"], link_node["crate_id"], slot)

        macros={"P":link_node['app_prefix'],
                "MPS_LINK_NODE_SIOC":link_node_name,
                "MPS_LINK_NODE_ID":link_node['lc1_node_id'],
                "MPS_LINK_NODE_TYPE":str(self.__link_node_type_to_number(link_node['type'])),
                "MPS_CONFIG_VERSION":self.config_version}
        self.__write_epics_db(path=path, template_name="link_node_info.template", macros=macros)

    def __link_node_type_to_number(self, ln_type):
        if ln_type == 'Digital':
            return 0
        elif ln_type == 'Mixed':
            return 2
        else:
            return 1

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

    def __write_analog_db(self, path, macros):
        """
        Write the records for analog inputs to the application EPIC database file.

        These records will be loaded once per each device.
        """
        self.__write_epics_db(path=path, template_name="analog_input.template", macros=macros)

    def __write_virtual_db(self, path, macros):
        """
        Write records for digital virtual inputs
        """
        self.__write_epics_db(path=path, template_name="virtual.template", macros=macros)

    def __write_link_node_channel_info_db(self, path, macros):
        self.__write_epics_db(path=path, template_name="link_node_channel_info.template", macros=macros)

    def __write_link_node_slot_info_db(self, path, macros):
        self.__write_epics_db(path=path, template_name="link_node_slot_info.template", macros=macros)

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

    def __write_mps_sf_cmd(self, path, template_name, macros):
        file = "{}mps_scale_factor.cmd".format(path)
        template = "{}epics_env/{}".format(self.template_path, template_name)
        self.__write_file_from_template(file=file, template=template, macros=macros)

    def __write_mps_analog_cmd(self, path, template_name, macros):
        file = "{}mps_analog_channels.cmd".format(path)
        template = "{}epics_env/{}".format(self.template_path, template_name)
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

def main(db_file, dest_path, template_path=None, app_id=None, 
         manager_info={'host': 'lcls-daemon2', 'port':1975}, verbose=False):

    if (template_path==None):
        template_path='templates/'

    # Generate the Mps application reader object
    mps_app_reader = MpsAppExporter(db_file, template_path, dest_path, app_id, manager_info, verbose)
#    mps_app_reader.pretty_print()
#    exit(0)

    # Print a report of the found applications
    if (verbose):
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
    parser.add_argument('--manager-host', metavar='host', help='Host for MpsManager server (default=lcls-daemon2)',
                        default='lcls-daemon2')
    parser.add_argument('--manager-port', metavar='port', help='Port for MpsManager server (default=1975)',
                        default=1975)

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
    create_dir(dest_path, clean=clean, debug=False)

    # If the template path is specified, check its format and if it exists
    if template_path:
        template_path = format_path(template_path)

        # Check is the template path exist
        if not os.path.exists(template_path):
            print("EPICS DB template directory '{}' not found.".format(template_path))
            exit(1)

    main(db_file=db_file, dest_path=dest_path, template_path=template_path, app_id=app_id,
         manager_info={'host':args.manager_host, 'port':args.manager_port}, verbose=verbose)
