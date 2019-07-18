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
from pprint import *

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
        self.areas = ['global2', 'GUNB', 'L0B', 'HTR', 'L1B', 'BC1B', 'L2B',
                      'BC2B', 'L3B', 'EXT', 'DOG', 'BYP',
                      'SLTH', 'SLTS', 'BSYH', 'BSYS', 'LTUH',
                      'LTUS', 'UNDH', 'UNDS', 'DMPH', 'DMPS', 
                      'FEEH', 'FEES']
        self.areas_in_order = self.areas

        # Open a session to the MPS database
        with MpsDbReader(db_file) as mps_db_session:

            # Extract the application information
            self.mps_name = MpsName(mps_db_session)
            self.__extract_alarms(mps_db_session)

#            pp=PrettyPrinter(indent=4)
#            pp.pprint(self.alarm_info)
#            exit(1)

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
          'ln' : {
            'mp01' : ['ln_PV', 'ln_PV', ... ]
            ...
          }
        }, { 'area': ... }, ... }
        """

        try:
            app_cards = mps_db_session.query(models.ApplicationCard).all()
            faults = mps_db_session.query(models.Fault).all()
            destinations = mps_db_session.query(models.BeamDestination).all()
        except exc.SQLAlchemyError as e:
            raise

        # Check if there were applications/faults defined in the database
        if len(app_cards) == 0:
            return

        if len(faults) == 0:
            return 

        # Alarms for app status (i.e. alarm when an APP is not updating MPS)
        for app_card in app_cards:
            area = self.check_area(app_card.area.upper())

            if area in self.alarm_info:
                alarm_area = self.alarm_info[area]
            else:
                alarm_area = {}
                alarm_area['faults'] = []
                alarm_area['apps'] = []
                alarm_area['link_nodes'] = {}
                self.alarm_info[area] = alarm_area

            # The $(BASE) macro defines in which central node this PV lives
            # Currenly it is set to SIOC:SYS2:MP01 in this script
            alarm_area['apps'].append('$(BASE):APP{}_STATUS'.format(app_card.global_id))

            link_node = format(app_card.link_node.location).upper()
            if link_node in alarm_area['link_nodes']:
                alarm_area['link_nodes'][link_node] = self.add_ln_alarms(app_card, alarm_area['link_nodes'][link_node])
            else:
                alarm_area['link_nodes'][link_node] = self.add_ln_alarms(app_card, None)
                
        # Alarms for faults for all other areas
        for fault in faults:
            pv = self.mps_name.getFaultName(fault)
            if (pv == None):
                pv = 'BASE:AREA:POSITION:FAULT'
            area = self.check_area(pv.split(":")[1].upper())
            
            if area in self.alarm_info:
                alarm_area = self.alarm_info[area]
            else:
                alarm_area = {}
                alarm_area['faults'] = []
                alarm_area['apps'] = []
                self.alarm_info[area] = alarm_area
            
            alarm_area['faults'].append(pv)

            
        # Alarms for beam destinations
        area = 'global2'
        alarm_area = {}
        alarm_area['faults'] = []
        alarm_area['apps'] = []
        for destination in destinations:
            pv = self.mps_name.getBeamDestinationName(destination)
            alarm_area['faults'].append(pv)
        self.alarm_info[area] = alarm_area

        # Save a list of areas in a separate array
        self.areas = []
        for area in self.alarm_info:
            if (area != 'NONE'):
                self.areas.append(area)
        
        self.areas = self.sort_areas()

    def sort_areas(self):
        print self.areas
        sorted_areas = []
        for a in self.areas_in_order:
            if a in self.areas:
                sorted_areas.append(a)
        return sorted_areas


    def add_ln_alarms(self, app_card, ln_pvs):
        if not ln_pvs:
            ln_pvs = []
        ln_pvs.append('{}:{}:MPS_EN'.format(app_card.link_node.get_pv_base(), app_card.get_card_id()))
        ln_pvs.append('{}:{}:TIM_LINK_STAT'.format(app_card.link_node.get_pv_base(), app_card.get_card_id()))
#        ln_pvs.append('{}:{}:THR_LOADED'.format(app_card.link_node.get_pv_base(), app_card.get_card_id()))
        return ln_pvs

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

    def generate_alarm_files(self, template_body_name,
                             template_header_name, template_include_name):
        """
        Generate the EPICS database and configuration files from the application data obtained by the
        extract_alarms method.

        The files will be written in the destination directory specified from the user (TOP),
        following the following structure:

        <TOP>/alarms

        Files: mps.alhConfig
               |- mps_global2.alhConfig
               | ...
               |- mps_<AREA>.alhConfig
                  |- mps_<AREA>_flt.alhConfig (faults)
                  |- mps_<AREA>_apps.alhConfig (app timeouts)
                  |- mps_<AREA>_mpXXX.alhConfig (link node XXX alarms)

        """
        print("==================================================")
        print("== Generating alarm handler files:              ==")
        print("==================================================")
        for area in self.areas_in_order:
            if not area in self.alarm_info:
                continue
            alarm_info = self.alarm_info[area]
#        for area, alarm_info in self.alarm_info.iteritems():
#            pp=PrettyPrinter(indent=4)
#            pp.pprint(self.alarm_info)
            include_files = []
            
            # Generate mps_<AREA>_faults.alhConfig file
            if len(alarm_info['faults']) > 0:
                alh_filename = '{}_faults'.format(area.lower())
                include_files.append('faults')
                alh_filename = 'mps_' + alh_filename + '.alhConfig'
                group_name = 'MPS:{}:FLT'.format(area.upper())
                group_alias = 'Faults'
                group_pv = group_name
                self.generate_alh_file(template_body_name, template_header_name,
                                       group_name, group_alias, group_pv,
                                       area, alarm_info['faults'],
                                       '{}{}'.format(self.dest_path, alh_filename))

            # Generate mps_<AREA>_apps.alhConfig file
            if len(alarm_info['apps']) > 0:
                alh_filename = '{}_apps'.format(area.lower())
                include_files.append('apps')
                alh_filename = 'mps_' + alh_filename + '.alhConfig'
                group_name = 'MPS:{}:APPS'.format(area.upper())
                group_alias = 'Applications'
                group_pv = group_name
                self.generate_alh_file(template_body_name, template_header_name,
                                       group_name, group_alias, group_pv,
                                       area, alarm_info['apps'],
                                       '{}{}'.format(self.dest_path, alh_filename))

            # Generate mps_<AREA>_mp<XX>.alhConfig files
            if 'link_nodes' in alarm_info:
                for link_node, link_node_pvs in alarm_info['link_nodes'].iteritems():
                    alh_filename = '{}_{}'.format(area.lower(), link_node.lower())
                    include_files.append(link_node.lower())
                    alh_filename = 'mps_' + alh_filename + '.alhConfig'
                    group_name = 'MPS:{}:{}'.format(area.upper(), link_node.upper())
                    group_alias = 'Link Node {}'.format(link_node.upper())
                    group_pv = group_name
                    self.generate_alh_file(template_body_name, template_header_name,
                                           group_name, group_alias, group_pv, 
                                           area, link_node_pvs,
                                           '{}{}'.format(self.dest_path, alh_filename))

            alh_include_filename = '{}mps_{}.alhConfig'.format(self.dest_path, area.lower())
            group_name = 'MPS:{}'.format(area.upper())
            group_alias = area.upper()
            group_pv = group_name
            self.generate_alh_include_file(template_header_name, template_include_name,
                                           group_name, group_alias, group_pv,
                                           area, include_files, alh_include_filename)

        self.generate_mps_alh_file(template_header_name, template_include_name)


    def generate_alh_include_file(self, template_header_name, template_include_name,
                                  group_name, group_alias, group_pv,
                                  area, include_files, alh_include_filename):
        """
        Generate alarm file with a list of include files
        """
        system_macro = 'mps'
        substitution_header_file = '{}mps_{}_header.substitution'.format(self.dest_path, area.lower())
        self.generate_substitution_header_file(substitution_header_file, template_header_name,
                                               group_name, group_alias, group_pv,
                                               area, system_macro)

        generated_template_header = '{}mps_{}.template.header'.format(self.dest_path, area.lower())
        self.run_msi(substitution_header_file, generated_template_header)

        substitution_include_file = '{}mps_{}_include.substitution'.format(self.dest_path, area.lower())
        self.generate_substitution_include_file(substitution_include_file, template_include_name,
                                                'mps', area, group_name, include_files)

        generated_template_body = '{}mps_{}.template.body'.format(self.dest_path, area.lower())
        self.run_msi(substitution_include_file, generated_template_body)

        self.concatenate_files(alh_include_filename, generated_template_header, generated_template_body)

        return


    def generate_mps_alh_file(self, template_header_name, template_include_name):
        area = 'mps'
        system_macro = 'all2'
        substitution_header_file = '{}mps_{}_header.substitution'.format(self.dest_path, area.lower())
        self.generate_substitution_header_file(substitution_header_file, template_header_name, 
                                               'ALL2:MPS:1', 'MPS', 'ALL2:MPS:1',
                                               area, system_macro)

        generated_template_header = '{}mps_{}.template.header'.format(self.dest_path, area.lower())
        self.run_msi(substitution_header_file, generated_template_header)

        substitution_include_file = '{}mps_{}_include.substitution'.format(self.dest_path, area.lower())
        self.generate_substitution_include_file(substitution_include_file, template_include_name,
                                                'all2', 'mps', 'ALL2:MPS:1', self.areas)

        generated_template_body = '{}mps_{}.template.body'.format(self.dest_path, area.lower())
        self.run_msi(substitution_include_file, generated_template_body)

        alh_file = '{}mps.alhConfig'.format(self.dest_path)
        self.concatenate_files(alh_file, generated_template_header, generated_template_body)

        return

    def generate_substitution_include_file(self, file_name, template_body_name, system, subsystem, 
                                           group_name, areas):
        with open(file_name, 'w') as f:
            f.write('file "{}alarms/{}" {{ pattern\n'.\
                        format(self.template_path, template_body_name))
            f.write('{SYSTEM, SUBSYSTEM, SUBSYSTEM_LOWER, GROUP_NAME, AREA_LOWER}\n')
#            for key, value in self.alarm_info.iteritems():
#                sys.stdout.write('| {0: >7} |      {1: >3}      | {2: >3}'.format(key, len(value['faults']), len(value['app'])))

            for area in areas:
                if system == 'mps' or system == 'MPS':
                    f.write('{{ "{}", "{}", "{}", "{}", "{}" }}\n'.\
                                format(system.upper(), subsystem.upper(),
                                       'mps_{}'.format(subsystem.lower()),
                                       group_name, area.lower()))
                else:
                    f.write('{{ "{}", "{}", "{}", "{}", "{}" }}\n'.\
                                format(system.upper(), subsystem.upper(),
                                       subsystem.lower(), group_name, area.lower()))
            f.write('}\n')

    def generate_substitution_header_file(self, file_name, template_header_name,
                                          group_name, group_alias, group_pv,
                                          area, system_macro):
        # Generate substitutions file
        with open(file_name, 'w') as f:
            f.write('file "{}alarms/{}" {{ pattern\n'.\
                        format(self.template_path, template_header_name))
            f.write('{GROUP_NAME, GROUP_ALIAS, GROUP_PV, AREA, SYSTEM, BASE}\n')
            f.write('{{ "{}", "{}", "{}", "{}", "{}", "SIOC:SYS2:MP01" }}\n'.\
                        format(group_name, group_alias, group_pv,
                               area.upper(), system_macro.upper()))
            f.write('}\n')

    def generate_substitution_body_file(self, file_name, template_body_name,
                                        group_name, area, system_macro, pvs):
        with open(file_name, 'w') as f:
            f.write('file "{}alarms/{}" {{ pattern\n'.\
                        format(self.template_path, template_body_name))
            f.write('{AREA, GROUP_NAME, SYSTEM, BASE, FAULT_PV}\n')
            for pv in pvs:
                f.write('{{ "{}", "{}", MPS, SIOC:SYS2:MP01 {} }}\n'.\
                            format(area.upper(), group_name, pv.upper()))
            f.write('}\n')

    def run_msi(self, substitution_file, template_file):
        msi_cmd = 'msi -V -S {} -o {}'.\
            format(substitution_file, template_file)
        os.system(msi_cmd)
        os.system('rm -f {}'.format(substitution_file))

    def concatenate_files(self, output, header, body):
        os.system('mv -f {} {}'.format(header, output))
        os.system('cat {} >> {}'.format(body, output))
        os.system('rm -f {}'.format(body))

    def generate_alh_file(self, template_body_name, template_header_name,
                          group_name, group_alias, group_pv, area, pvs, alh_filename):
        # Generate substitutions file
        substitution_header_file = '{}mps_{}_header.substitution'.format(self.dest_path, area.lower())
        self.generate_substitution_header_file(substitution_header_file, template_header_name, 
                                               group_name, group_alias, group_pv,
                                               area, 'MPS')

        substitution_body_file = '{}mps_{}_body.substitution'.format(self.dest_path, area.lower())
        self.generate_substitution_body_file(substitution_body_file, template_body_name,
                                             group_name, area, 'MPS', pvs)

        generated_template_header = '{}mps_{}.template.header'.format(self.dest_path, area.lower())
        self.run_msi(substitution_header_file, generated_template_header)

        generated_template_body = '{}mps_{}.template.body'.format(self.dest_path, area.lower())
        self.run_msi(substitution_body_file, generated_template_body)

        self.concatenate_files(alh_filename, generated_template_header, generated_template_body)

    def print_alarm_data(self):
        """
        Print the content of the application data obtained by the extract_alarms method.
        """
        print('+- Area --+- # Fault PVs -+- # App PVs -+- # LN PVs -+')
        for key, value in self.alarm_info.iteritems():
            ln_pvs = 0
            if 'link_nodes' in value:
                for ln, pvs in value['link_nodes'].iteritems():
                    ln_pvs += len(pvs)

            sys.stdout.write('| {0: >7} |      {1: >3}      |    {2: >3}      |   {2: > 3}      |'.\
                                 format(key, len(value['faults']), len(value['apps']), ln_pvs))
#            for pv in value['global_id']:
#                sys.stdout.write('{0: >3} '.format(pv))
            print('')
        print('+---------+---------------+-------------+------------+')

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
    mps_alarm_reader.generate_alarm_files('mps_group.template',
                                          'mps_group_header.template',
                                          'mps_include.template')

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
