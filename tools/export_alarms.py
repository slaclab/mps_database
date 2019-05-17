#!/usr/bin/env python

from mps_config import MPSConfig, models
from mps_names import MpsName
from sqlalchemy import func, exc
import argparse
import sys
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


class MpsAlarmReader:
    """
    This class extract all the necessary information of each application
    defined in the MPS database, necessary to generate the alarm files
    """
    def __init__(self, db_file, template_path, dest_path, app_id, verbose):

        self.template_path = template_path
        self.dest_path = dest_path
        self.verbose = verbose
        self.app_id = app_id
        self.alarm_info = {}
        self.areas = ['GUNB', 'L0B', 'HTR', 'L1B', 'BC1B', 'L2B',
                      'BC2B', 'L3B', 'EXT', 'DOG', 'BYP',
                      'SLTH', 'BSYH', 'LTUH', 'UNDH', 'DMPH', 'FEEH',
                      'SLTS', 'BSYS', 'LTUS', 'UNDS', 'DMPS', 'FEES']

        # Open a session to the MPS database
        with MpsDbReader(db_file) as mps_db_session:

            # Extract the application information
            self.mps_name = MpsName(mps_db_session)
            self.__extract_alarms(mps_db_session)


    def __extract_alarms(self, mps_db_session):
        """
        Extract all alarm information from the MPS database. A session to the
        database is passed as an argument.
        
        Returns the following structure:

        alarm_info = {
        'area name': {
          'area': 'area name, e.g. GUNB or global2'
          'faults': ['fault_PV', 'fault_PV, ... ]
          'apps': ['app_PV', 'app_PV, ... ]
        }, { 'area': ... }, ... }
        """

        try:
            app_cards = mps_db_session.query(models.ApplicationCard).all()
            faults = mps_db_session.query(models.Fault).all()
        except exc.SQLAlchemyError as e:
            raise

        # Check if there were applications/faults defined in the database
        if len(app_cards) == 0:
            return

        if len(faults) == 0:
            return 

        # Faults for Global area
        for app_card in app_cards:
            area = self.check_area(app_card.area.upper())

            if area in self.alarm_info:
                alarm_area = self.alarm_info[area]
            else:
                alarm_area = {}
                alarm_area['pv'] = []
                alarm_area['app'] = []
                self.alarm_info[area] = alarm_area

            alarm_area['app'].append('SIOC:SYS2:MP01:APP{}_STATUS'.format(app_card.global_id))


        # Faults for all other areas
        for fault in faults:
            pv = self.mps_name.getFaultName(fault)
            area = self.check_area(pv.split(":")[1].upper())
            
            if area in self.alarm_info:
                alarm_area = self.alarm_info[area]
            else:
                alarm_area = {}
                alarm_area['pv'] = []
                alarm_area['app'] = []
                self.alarm_info[area] = alarm_area
            
            alarm_area['pv'].append(pv)
            
    def check_area(self, area):
        if not area in self.areas:
            if (area.startswith('BPN')):
                return 'BYP'
            elif (area == 'SPH'):
                return 'SLTH'
            elif (area == 'SPS'):
                return 'SLTS'
            else:
                return 'NONE'
        else:
            return area

    def generate_alarm_files(self, template_body_name, template_header_name):
        """
        Generate the EPICS database and configuration files from the application data obtained by the
        extract_alarms method.

        The files will be written in the destination directory specified from the user (TOP),
        following the following structure:

        <TOP>/alarms
        

        """
        print("==================================================")
        print("== Generating alarm handler files:              ==")
        print("==================================================")
            

        for area, alarm_info in self.alarm_info.iteritems():
            alh_filename = '{}mps_{}.alhConfig'.format(self.dest_path, area.lower())
            self.generate_alh_file(template_body_name, template_header_name,
                                   area, alarm_info['pv'], alh_filename)
            alh_filename = '{}mps_{}_apps.alhConfig'.format(self.dest_path, area.lower())
            self.generate_alh_file(template_body_name, template_header_name,
                                   area, alarm_info['app'], alh_filename)

    def generate_alh_file(self, template_body_name, template_header_name, area, pvs, alh_filename):
        # Generate substitutions file
        substitution_header_file = '{}mps_{}_header.substitution'.format(self.dest_path, area.lower())
        with open(substitution_header_file, 'w') as f:
            f.write('file "{}alarms/common/{}" {{ pattern\n'.format(self.template_path, template_header_name))
            f.write('{AREA}\n')
            f.write('{{ {} }}\n'.format(area.upper()))
            f.write('}\n')

        substitution_body_file = '{}mps_{}_body.substitution'.format(self.dest_path, area.lower())
        with open(substitution_body_file, 'w') as f:
            f.write('file "{}alarms/common/{}" {{ pattern\n'.format(self.template_path, template_body_name))
            f.write('{AREA, FAULT_PV}\n')
            for pv in pvs:
                f.write('{{ {}, {} }}\n'.format(area.upper(), pv.upper()))
            f.write('}\n')

        generated_template_header = '{}mps_{}.template.header'.format(self.dest_path, area.lower())
        msi_header_cmd = 'msi -V -S {} -o {}'.\
            format(substitution_header_file, generated_template_header)
        os.system(msi_header_cmd)

        generated_template_body = '{}mps_{}.template.body'.format(self.dest_path, area.lower())
        msi_cmd = 'msi -V -S {} -o {}'.\
            format(substitution_body_file, generated_template_body)
        os.system(msi_cmd)

        # cleanup
        os.system('rm -f {}'.format(substitution_header_file))
        os.system('rm -f {}'.format(substitution_body_file))

        os.system('mv -f {} {}'.format(generated_template_header, alh_filename))
        os.system('cat {} >> {}'.format(generated_template_body, alh_filename))
        os.system('rm -f {}'.format(generated_template_body))


    def print_alarm_data(self):
        """
        Print the content of the application data obtained by the extract_alarms method.
        """
        print('+- Area --+- # Alarm PVs -+- # App PVs -+')
        for key, value in self.alarm_info.iteritems():
            sys.stdout.write('| {0: >5}   |      {1: >3}      | {2: >3}'.format(key, len(value['pv']), len(value['app'])))
#            for pv in value['global_id']:
#                sys.stdout.write('{0: >3} '.format(pv))
            print('')
        print("===================================")

#################
### Main Body ###
#################

def main(db_file, dest_path, template_path=None, app_id=None, verbose=False):

    if (template_path==None):
        template_path='templates/'

    # Generate the Mps application reader object
    mps_alarm_reader = MpsAlarmReader(db_file, template_path, dest_path, app_id, verbose)

    # Print a report of the found applications
    mps_alarm_reader.print_alarm_data()

    # Generate the alarm files
    mps_alarm_reader.generate_alarm_files('mps_area.template', 'mps_area_header.template')

if __name__ == "__main__":

    # Parse input arguments
    parser = argparse.ArgumentParser(description='Export MPS alarms')
    parser.add_argument('--db', metavar='database', required=True,
                        help='MPS SQLite database file')
    parser.add_argument('--dest', metavar='destination', required=True,
                        help='Destination location of the resulting EPICS database')
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

    main(db_file=db_file, dest_path=dest_path, template_path=template_path, app_id = app_id, verbose=verbose)
