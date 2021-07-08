#!/usr/bin/env python

from mps_database.mps_config import MPSConfig, models
from mps_database.tools.mps_names import MpsName
from sqlalchemy import func, exc
from .mps_app_reader import MpsAppReader
import argparse
import os
import errno
import re
import shutil
import datetime
import ipaddress

def format_path(path):
    """
    (str) -> str
    Make sure that path ends with a backslash '/'
    """
    return path if path.endswith('/') else path + '/'

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
        self.manager_info = manager_info
        self.cn0_path = '{}cn1/'.format(self.dest_path)
        self.cn1_path = '{}cn2/'.format(self.dest_path)
        self.cn2_path = '{}cn3/'.format(self.dest_path)

    def generate_cn_db(self):
      # Generate device inputs
      self.generate_digital_db_by_app_id(app_id)
      # Generate analog inputs
      self.generate_analog_db(app_id)
      # Generate beam destinations
      self.generate_dest_db()
      # Generate ignore conditions
      self.generate_condition_db()
      # Generate all ID JSON file
      self.generate_app_ids()

    def generate_app_ids(self):
      cn1 = []
      cn2 = []
      for app in self.digital_apps + self.analog_apps:
        if app["central_node"] in [0,2]:
          cn1.append(app['app_id'])
        elif app["central_node"] in [1]:
          cn2.append(app['app_id'])
      for aid in sorted(cn1):
          macros = { 'APP_ID':'{0}'.format(aid)}
          self.__write_disp(path=self.cn0_path, macros=macros)
      for aid in sorted(cn2):
          macros = { 'APP_ID':'{0}'.format(aid)}
          self.__write_disp(path=self.cn1_path, macros=macros)
          

    def generate_condition_db(self):
      for condition in self.conditions:
        macros = { 'NAME':'{0}'.format(condition['name']),
                   'DESC':'{0}'.format(condition['description']), 
                   'ID':'{0}'.format(condition["db_id"]) }
        self.__write_condition_db(path=self.cn0_path, macros=macros)
        self.__write_condition_db(path=self.cn1_path, macros=macros)
        self.__write_condition_db(path=self.cn2_path, macros=macros)             

    def generate_dest_db(self):
      macros = { 'NUM':'{0}'.format(len(self.beam_classes))}
      self.__write_num_pc_db(path=self.cn0_path, macros=macros)
      self.__write_num_pc_db(path=self.cn1_path, macros=macros)
      self.__write_num_pc_db(path=self.cn2_path, macros=macros)
      for beam_class in self.beam_classes:
        macros = { 'NUM':'{0}'.format(beam_class["number"]),
                   'NAME':'{0}'.format(beam_class["name"]),
                   'DESC':'{0}'.format(beam_class["description"]),
                   'CHRG':'{0}'.format(beam_class["total_charge"]),
                   'SPACE':'{0}'.format(beam_class["min_period"]),
                   'TIME':'{0}'.format(beam_class["integration_window"]) }
        self.__write_pc_def_db(path=self.cn0_path, macros=macros)
        self.__write_pc_def_db(path=self.cn1_path, macros=macros)
        self.__write_pc_def_db(path=self.cn2_path, macros=macros)
      for beam_destination in self.beam_destinations:
        macros = { 'DEST':'{0}'.format(beam_destination["name"]),
                   'ID':'{0}'.format(beam_destination["id"]) }
        self.__write_dest_db(path=self.cn0_path, macros=macros)
        self.__write_dest_db(path=self.cn1_path, macros=macros)
        self.__write_dest_db(path=self.cn2_path, macros=macros)              

    def generate_digital_db_by_app_id(self, app_id):
      for app in self.digital_apps:
        macros = { 'APP_ID':'{0}'.format(app['app_id']),
                   'TYPE':'{0}'.format(app['name']),
                   'LOCA':'{0}'.format(app['physical']),
                   'SLOT':'{0}'.format(app['slot_number']),
                   'ID':'{0}'.format(app['db_id']) }
        if app['central_node'] in [0,2]:
          self.__write_app_db(path=self.cn0_path, macros=macros)
          if app['central_node'] in [2]:
            self.__write_app_db(path=self.cn2_path, macros=macros)
        elif app['central_node'] in [1]:
          self.__write_app_db(path=self.cn1_path, macros=macros)
        for device in app['devices']:
          for input in device['inputs']:
            macros = { 'P':'{0}:{1}'.format(device['prefix'],input['name']),
                       'ONAM':'{0}'.format(input['one_name']),
                       'ZNAM':'{0}'.format(input['zero_name']),
                       'CR':'{0}'.format(app['crate_key']),
                       'CA':'{0}'.format(app['app_id']),
                       'CH':'{0}'.format(input['bit_position']),
                       'ID':'{0}'.format(input['db_id']),
                       'ZSV':'{0}'.format(input['zero_severity']),
                       'OSV':'{0}'.format(input['one_severity'])}
            if app['central_node'] in [0,2]:
              self.__write_digital_db(path=self.cn0_path, macros=macros)
              if app['central_node'] in [2]:
                self.__write_digital_db(path=self.cn2_path, macros=macros)
            elif app['central_node'] in [1]:
              self.__write_digital_db(path=self.cn1_path, macros=macros)
          for fault in device["faults"]:
            macros = { 'P':'{0}:{1}'.format(device['prefix'],fault['name']),
                       'DESC':'{0}'.format(fault['description']),
                       'ID':'{0}'.format(fault['id']) }
            if app['central_node'] in [0,2]:
              self.__write_fault_db(path=self.cn0_path, macros=macros)
              if app['central_node'] in [2]:
                self.__write_fault_db(path=self.cn2_path, macros=macros)
            elif app['central_node'] in [1]:
              self.__write_fault_db(path=self.cn1_path, macros=macros)
            for idx in range(len(fault['states'])):
              macros = { 'P':'{0}:{1}_{2}'.format(device['prefix'],fault['name'],fault['states'][idx]),
                         'ID':'{0}'.format(fault["fs_id"][idx]),
                         'DESC':'{0}'.format(fault["fs_desc"][idx]) }
              if app['central_node'] in [0,2]:
                self.__write_fault_state_db(path=self.cn0_path, macros=macros)
                if app['central_node'] in [2]:
                  self.__write_fault_state_db(path=self.cn2_path, macros=macros)
              elif app['central_node'] in [1]:
                self.__write_fault_state_db(path=self.cn1_path, macros=macros)                

    def generate_analog_db(self, app_id):
      for app in self.analog_apps:
        macros = { 'APP_ID':'{0}'.format(app['app_id']),
                   'TYPE':'{0}'.format(app['name']),
                   'LOCA':'{0}'.format(app['physical']),
                   'SLOT':'{0}'.format(app['slot_number']),
                   'ID':'{0}'.format(app['db_id']) }
        if app['central_node'] in [0,2]:
          self.__write_app_db(path=self.cn0_path, macros=macros)
          if app['central_node'] in [2]:
            self.__write_app_db(path=self.cn2_path, macros=macros)
        elif app['central_node'] in [1]:
          self.__write_app_db(path=self.cn1_path, macros=macros)
        for device in app['devices']:
          for key, fault in list(device['faults'].items()):    
            macros = { 'P':"{0}:{1}".format(device['prefix'],fault['name']),
                       'ID':'{0}'.format(device['db_id']),
                       'INT':'{0}'.format(fault['integrators'][0]) }
            if app['central_node'] in [0,2]:
              self.__write_analog_byp_db(path=self.cn0_path, macros=macros)
              if app['central_node'] in [2]:
                self.__write_analog_byp_db(path=self.cn2_path, macros=macros)
            elif app['central_node'] in [1]:
              self.__write_analog_byp_db(path=self.cn1_path, macros=macros)
            macros = { 'P':'{0}:{1}'.format(device['prefix'],fault['name']),
                       'DESC':'{0}'.format(fault['description']),
                       'ID':'{0}'.format(fault['id']) }
            if app['central_node'] in [0,2]:
              self.__write_fault_db(path=self.cn0_path, macros=macros)
              if app['central_node'] in [2]:
                self.__write_fault_db(path=self.cn2_path, macros=macros)
            elif app['central_node'] in [1]:
              self.__write_fault_db(path=self.cn1_path, macros=macros)
            for idx in range(len(fault['bit_positions'])):
              macros = { 'P':"{0}:{1}_T{2}".format(device['prefix'],fault['name'],fault['bit_positions'][idx]),
                         'CR':'{0}'.format(app['crate_key']),
                         'CA':'{0}'.format(app['app_id']),
                         'CH':'{0}'.format(device['channel']),
                         'ID':'{0}'.format(device['db_id']),
                         'MASK':'{0}'.format(fault['mask'][idx]) }       
              if app['central_node'] in [0,2]:
                self.__write_analog_ch_db(path=self.cn0_path, macros=macros)
                if app['central_node'] in [2]:
                  self.__write_analog_ch_db(path=self.cn2_path, macros=macros)
              elif app['central_node'] in [1]:
                self.__write_analog_ch_db(path=self.cn1_path, macros=macros)
                
              macros = { 'P':'{0}:{1}_{2}'.format(device['prefix'],fault['name'],fault['states'][idx]),
                         'ID':'{0}'.format(fault["fs_id"][idx]),
                         'DESC':'{0}'.format(fault["fs_desc"][idx]) }
              if app['central_node'] in [0,2]:
                self.__write_fault_state_db(path=self.cn0_path, macros=macros)
                if app['central_node'] in [2]:
                  self.__write_fault_state_db(path=self.cn2_path, macros=macros)
              elif app['central_node'] in [1]:
                self.__write_fault_state_db(path=self.cn1_path, macros=macros)                   
            

    def __write_digital_db(self, path, macros):
        """
        Write the digital CN records to the CN EPICS database file.
        These records will be loaded once per each device.
        """
        self.__write_epics_db(path=path,filename='device_inputs.db',template_name="cn_device_input.template", macros=macros)

    def __write_num_pc_db(self, path, macros):
        """
        Write the digital CN records to the CN EPICS database file.
        These records will be loaded once per each device.
        """
        self.__write_epics_db(path=path,filename='destinations.db',template_name="cn_num_beam_classes.template", macros=macros)
 
    def __write_disp(self, path, macros):
        """
        Write the LN IOC related environmental variable file.

        This environmental variable will be loaded by all link nodes.
        """
        file = "{}app_id.json".format(path)
        template = "{}scripts/{}".format(self.template_path, "app_id_disp.template")
        self.__write_file_from_template(file=file, template=template, macros=macros)

    def __write_pc_def_db(self, path, macros):
        """
        Write the digital CN records to the CN EPICS database file.
        These records will be loaded once per each device.
        """
        self.__write_epics_db(path=path,filename='destinations.db',template_name="cn_beam_class_definition.template", macros=macros)

    def __write_dest_db(self, path, macros):
        """
        Write the digital CN records to the CN EPICS database file.
        These records will be loaded once per each device.
        """
        self.__write_epics_db(path=path,filename='destinations.db',template_name="cn_beam_class_destination.template", macros=macros)

    def __write_app_db(self, path, macros):
        """
        Write the digital CN records to the CN EPICS database file.
        These records will be loaded once per each device.
        """
        self.__write_epics_db(path=path,filename='apps.db',template_name="cn_app_timeout.template", macros=macros)

    def __write_condition_db(self, path, macros):
        """
        Write the digital CN records to the CN EPICS database file.
        These records will be loaded once per each device.
        """
        self.__write_epics_db(path=path,filename='conditions.db',template_name="cn_condition.template", macros=macros)

    def __write_analog_ch_db(self, path, macros):
        """
        Write the digital CN records to the CN EPICS database file.
        These records will be loaded once per each device.
        """
        self.__write_epics_db(path=path, filename='analog_devices.db', template_name="cn_analog_fault.template", macros=macros)

    def __write_analog_byp_db(self, path, macros):
        """
        Write the digital CN records to the CN EPICS database file.
        These records will be loaded once per each device.
        """
        self.__write_epics_db(path=path, filename='analog_devices.db', template_name="cn_analog_device.template", macros=macros)

    def __write_fault_db(self, path, macros):
        """
        Write the digital CN records to the CN EPICS database file.
        These records will be loaded once per each device.
        """
        self.__write_epics_db(path=path, filename='faults.db', template_name="cn_fault.template", macros=macros)

    def __write_fault_state_db(self, path, macros):
        """
        Write the digital CN records to the CN EPICS database file.
        These records will be loaded once per each device.
        """
        self.__write_epics_db(path=path, filename='fault_states.db', template_name="cn_fault_states.template", macros=macros)
    
    def __write_epics_db(self, path,filename,template_name, macros):
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
        #print macros.items()
        for k, v in list(macros.items()):
            text = re.sub(r'\$\(({key}|{key},[^)]*)\)'.format(key=k),v, text)

        return text
        




#################
### Main Body ###
#################

def main(db_file, dest_path, template_path=None, app_id=None, 
         manager_info={'host': 'lcls-daemon2', 'port':1975}, verbose=False):

    if (template_path==None):
        template_path='templates/'

    mps_cn_reader = MpsAppExporter(db_file, template_path, dest_path, app_id, manager_info, verbose)

    if (verbose):
        mps_cn_reader.print_app_data()

    # Generated the application output file
    mps_cn_reader.generate_cn_db()

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
        print(('Exporting databases for AppId={}'.format(app_id)))
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
            print(("EPICS DB template directory '{}' not found.".format(template_path)))
            exit(1)

    main(db_file=db_file, dest_path=dest_path, template_path=template_path, app_id=app_id,
         manager_info={'host':args.manager_host, 'port':args.manager_port}, verbose=verbose)
