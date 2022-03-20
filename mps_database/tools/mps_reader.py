from mps_database.mps_config import MPSConfig, models
from mps_database.tools.mps_names import MpsName
from sqlalchemy import func, exc
import argparse
import os
import errno
import re
import shutil
import json
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

class MpsReader:

    def __init__(self,db_file,dest_path,template_path,clean,verbose=False):
        self.db_file=db_file
        self.config_version = os.path.basename(db_file).lstrip("mps_config-").rstrip(".db")
        # Check formatting of the destination path
        dest_path = self.format_path(dest_path)
        # Create a new clean output directory in the specified path
        self.create_dir(dest_path, clean=clean, debug=verbose)
        self.dest_path = dest_path
        self.display_path = '{}display/'.format(self.dest_path)
        self.alarm_path = '{}alarms/'.format(self.dest_path)
        self.report_path = '{}reports/build/'.format(self.dest_path)
        self.checkout_path = '{}checkout/'.format(self.dest_path)
        self.create_dir('{0}'.format(self.report_path))
        self.cn0_path = '{}central_node_db/cn1/'.format(self.dest_path)
        self.cn1_path = '{}central_node_db/cn2/'.format(self.dest_path)
        self.cn2_path = '{}central_node_db/cn3/'.format(self.dest_path)
        self.mps_names = None
        self.non_link_node_types = ["BPMS", "BLEN", "FARC", "TORO", "WIRE"]
        self.lc1_areas = ["CLTS","BSYS","BSYH","LTUS","LTUH","UNDS","UNDH","FEES","FEEH","LTU0","UND0","BSY0","DMP0","DMPH","DMPS"]
        self.hard_areas = ['BSYH','LTUH','UNDH','DMPH','FEEH']
        self.soft_areas = ['CLTS','BSYS','LTUS','UNDS','FEES','DMPS']
        self.nc_int0_cycles = 2
        self.nc_int1_cycles = 179
        self.sc_int0_cycles = 1023 #1023 is biggest value for this register --> 1023/910000 = 1 ms integration
        self.sc_int1_cycles = 1023
        self.cn0 = [2,3,4,5,6,7,8,9,10,11]
        self.cn1 = [12,13,14,15,16,17,18,19,20,21,22,23]
        self.cn2 = [0,1]
        self.database = db_file
        self.mbbi_strings = ['ZRST','ONST','TWST','THST','FRST','FVST','SXST','SVST','EIST','NIST','TEST','ELST','TVST','TTST','FTST','FFST']
        self.mbbi_vals = ['ZRVL','ONVL','TWVL','THVL','FRVL','FVVL','SXVL','SVVL','EIVL','NIVL','TEVL','ELVL','TVVL','TTVL','FTVL','FFVL']
        self.mbbi_sevr = ['ZRSV','ONSV','TWSV','THSV','FRSV','FVSV','SXSV','SVSV','EISV','NISV','TWSV','ELSV','TVSV','TTSV','FTSV','FFSV']
        self.lblms = []
        self.pblms = []
        self.cblms = []
        self.bpms = []
        
        # If the template path is specified, check its format and if it exists
        if template_path:
            template_path = self.format_path(template_path)
            # Check is the template path exist
            if not os.path.exists(template_path):
                print(template_path)
                print(("EPICS DB template directory '{}' not found.".alarm(template_path)))
                exit(1)
        self.template_path = template_path

    def initialize_mps_names(self,session):
      self.mps_names = MpsName(session)

    def get_app_path(self,link_node,slot):
      if slot == 1:
        slot = 2
      return '{}link_node_db/app_db/{}/{:04}/{:02}/'.format(self.dest_path,link_node.cpu, link_node.crate.crate_id, slot)

    def get_bay_number(self,channel):
      if channel < 3:
        return 0
      elif channel >2 and channel < 6:
        return 1
      else:
        return None

    def get_faults(self,device):
      fault_inputs = device.fault_outputs
      faults = []
      for fi in fault_inputs:
        faults.append(fi.fault)
      return faults

    def get_analog_type_name(self, device_type_name):
        """
        Return the fourth PV field for the analog measument type 
        according to the device type:
          * SOLN, BEND => CURRENT
          * PBLM, LBLM, CBLM => LOSS
          * TORO, FARC => CHARGE
        """
        if device_type_name in ["SOLN", "BEND", "KICK","BACT"]:
            return "BACT"
        elif device_type_name in ["PBLM", "LBLM", "CBLM", "BLM", "FADC","WF",'SBLM']:
            return "LOSS"
        elif device_type_name in ["TORO", "FARC"]:
            return "CHARGE"
        elif device_type_name in ['BPMS']:
            return ""
        elif device_type_name in ['BLEN']:
            return ""
        elif device_type_name in ['TEST']:
            return 'TEST'
        else:
            raise ValueError("Function \"get_analog_type_name(device_type_name={})\". Invalid device type name"
                             .format(device_type_name))

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
        if device_type_name in ["SOLN", "BEND","BLEN","KICK","BACT"]:
            # Solenoid devices use 'uA'.
            return "GeV/c"
        elif device_type_name in ["LBLM","PBLM","FADC","WF",'SBLM','TEST']:
            # Beam loss monitors set threshold in Volts initially
            return "raw"
        elif device_type_name in ['BLM','CBLM']:
            return 'mV'
        elif device_type_name == "BPMS":
            # For BPM, the units depend on the type of fault
            if fault_name in ["X", "Y"]:
                # Fault X, Y use 'mm'
                return "mm"
            elif fault_name == "CHRG":
                # TIMIT uses 'Nel'
                return "pC"
            elif fault_name == "CHRG_DIFF":
                return "pC"
            elif fault_name == "CHRGDIFF":
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

    def get_fault_index(self, device_type_name, fault_name, channel_number):
        """
        Get the 'fault_index' used in the EPICS DB.
        The fault index is appication specific as follows:
          * SOLN, BEND, PBLM, LBLM, BLM => (X)(Y), X=input channel(0-2), Y=Integration channel (0-3)
          * BPM     => (X),    X=Channel (0:X, 1:Y, 2, CHRG)
          * TORO,FC => (X),    X=Channel (0:Charge, 1:Difference)
          * BLEN    => 0
        """
        if device_type_name in ["SOLN", "BEND", "BLEN", "KICK","BACT"]:
            integration_channel = 0
            return "{}{}".format(channel_number,integration_channel)
        elif device_type_name in ["PBLM", "CBLM", "LBLM", "BLM","FADC","WF",'TEST']:
            # For BLM devices type, the fault name is "Ix",
            # where x is the integration channel
            integration_channel = 0
            integration_channel = int(fault_name.split('_')[0][-1])

            if integration_channel not in list(range(4)):
                raise ValueError("Function \"__get_fault_index(device_type_name={}, fault_name={}, channel_number={})\".\
                                Integration channel = {} out of range [0:3]".format(device_type_name, fault_name,
                                    channel_number, integration_channel))
            if channel_number > 2:
              channel_number = channel_number - 3

            return "{}{}".format(channel_number, integration_channel)
        else:
            # For other application, the get index from the following 2-D dict
            bpm_fault_index = { "X":"0", "Y":"1", "CHRG":"2","CHRG_DIFF":"2","CHRGDIFF":"2" }
            bcm_fault_index = { "CHARGE":"0", "DIFF": "1" }
            fault_indexes = {   "BPMS":bpm_fault_index,
                                "FARC":bcm_fault_index,
                                "TORO":bcm_fault_index }
            return fault_indexes[device_type_name][fault_name]

    def get_app_type_name(self, device_type_name):
        """
        Get the app type name used in the EPICS DB.
        The name is application specific as follows:
          * SOLN, BEND, PBLM, LBLM, BLM => BLM
          * BPMS       => BPM
          * TORO, FARC => BCM
        """
        if device_type_name in ["SOLN", "BEND", "PBLM", "CBLM", "LBLM", "BLEN", "BLM", "KICK","FADC","BACT","WF",'TEST']:
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

    def create_dir(self,path, clean=False, debug=False):
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
                print(("Directory '{}' exists. Removing it...".format(dir_name)))

            shutil.rmtree(dir_name, ignore_errors=True)
            dir_exist = False
        if not dir_exist:
            if debug:
                print(("Directory '{}' does not exist. Creating it...".format(dir_name)))
            try:
                os.makedirs(dir_name)

                if debug:
                    print("Directory created.")
            except OSError as exc: # Guard against race condition
                if exc.errno != errno.EEXIST:
                    raise

    def link_node_type_to_number(self, ln_type):
        if ln_type == 'Digital':
            return 0
        elif ln_type == 'Mixed':
            return 2
        else:
            return 1

    def exchange(self,string):
      name = string.split(":")
      name.insert(3,"3")
      name = ":".join(name)
      return name

    def format_path(self,path):
        """
        (str) -> str
        Make sure that path ends with a backslash '/'
        """
        return path if path.endswith('/') else path + '/'

    def write_json_file(self,filename,macros):
        self.create_dir(filename)
        with open(filename,'a') as file:
          json.dump(macros,file)

    def write_link_node_channel_info_db(self, path, macros):
        self.write_epics_db(path=path,filename='mps.db', template_name="link_node_channel_info.template", macros=macros)

    def write_epics_env(self, path, template_name, macros):
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
        self.write_file_from_template(file=file, template=template, macros=macros)

    def write_epics_db(self, path,filename, template_name, macros):
        """
        Write the EPICS DB file into the 'path' directory.

        The resulting file is named "mps.db". Calling this function
        multiple times, will append the results into the same file.

        The file is created from the template file located in the directory
        "epics_db" inside the global template directory, substituting the
        macros definitions.
        """
        file = "{0}{1}".format(path,filename)
        template = "{}epics_db/{}".format(self.template_path, template_name)
        self.write_file_from_template(file=file, template=template, macros=macros)

    def write_fw_config(self, path, template_name, macros):
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
        self.write_file_from_template(file=file, template=template, macros=macros)

    def write_ui_file(self, path, template_name, macros):
        template = '{}display/{}'.format(self.template_path, template_name)
        self.write_file_from_template(file=path,template=template,macros=macros)

    def write_alarm_file(self, path, template_name, macros):
        template = '{}alarms/{}'.format(self.template_path, template_name)
        self.write_file_from_template(file=path,template=template,macros=macros)

    def write_logic_json(self, path,filename, template_name, macros):
        """
        Write the EPICS DB file into the 'path' directory.

        The resulting file is named "mps.db". Calling this function
        multiple times, will append the results into the same file.

        The file is created from the template file located in the directory
        "epics_db" inside the global template directory, substituting the
        macros definitions.
        """
        file = "{0}{1}".format(path,filename)
        template = "{}logic/{}".format(self.template_path, template_name)
        self.write_file_from_template(file=file, template=template, macros=macros)

    def write_file_from_template(self, file, template, macros):
        """
        Genetic method to write a file from a template, substituting the
        passed macro definitions.

        The output file is opened in append mode, so calling this function
        pointing to the same file will add content to the file.

        If the directory of the output file does not exist, it will be created.
        """
        self.create_dir(file)
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
        #print macros.items()
        for k, v in list(macros.items()):
            text = re.sub(r'\$\(({key}|{key},[^)]*)\)'.format(key=k),v, text)

        return text
