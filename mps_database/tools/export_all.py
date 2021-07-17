#!/usr/bin/env python

from mps_database.mps_config import MPSConfig, models
from mps_database.tools.mps_names import MpsName
from mps_database import ioc_tools
from sqlalchemy import func, exc
from .mps_app_reader import MpsAppReader
import argparse
import time
import os
import subprocess
import errno
import re
import shutil
import datetime
import ipaddress
import json

def to_bool(s):
    if s:
      return 1
    else:
      return 0

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

def format_path(path):
    """
    (str) -> str
    Make sure that path ends with a backslash '/'
    """
    return path if path.endswith('/') else path + '/'

class MpsExporter(MpsAppReader):
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
        self.lc1_areas = ["CLTS","BSYS","BSYH","LTUS","LTUH","UNDS","UNDH","FEES","FEEH"]
        self.cn0_path = '{}central_node_db/cn1/'.format(self.dest_path)
        self.cn1_path = '{}central_node_db/cn2/'.format(self.dest_path)
        self.cn2_path = '{}central_node_db/cn3/'.format(self.dest_path)
        self.display_path = '{}display/'.format(self.dest_path)
        self.checkout_path = '{}checkout/'.format(self.dest_path)
        self.database = db_file

    def generate_ln_epics_db(self):
        """
        Generate the EPICS database and configuration files for link nodes from the application data obtained by the
        extract_apps method.

        The files will be written in the destination directory specified from the user (TOP),
        following the following structure:

        <TOP>link_node_db/app_db/<cpu_name>/<crate_id>/<slot_number>/

        Using the <cpu_name>, <crate_id>, and <slot_number> defined in each application.

        """
        # First generate the generic PVs and environment variables for each carrier in the system
        for ln_name, ln in list(self.link_nodes.items()):
          self.__write_lc1_info_config(ln)
          installed = list(ln['slots'].keys())
          if ln['analog_slot'] == 2:
            for slot in range(8):
              if slot in installed:
                if slot == 2 and 1 in installed:
                    continue
                app_prefix = ln['slots'][slot]['pv_base']
                if slot == 1:
                  slot = 2
                app_path = '{}link_node_db/app_db/{}/{:04}/{:02}/'.format(self.dest_path, ln["cpu_name"], ln["crate_id"], slot)
                self.__write_prefix_env(path=app_path, macros={"P":app_prefix,
                                                               "MPS_LINK_NODE":ln_name,
                                                               "MPS_DB_VERSION":self.config_version,
                                                               "DATE":datetime.datetime.now().strftime('%Y.%m.%d-%H:%M:%S'),
                                                               "MPS_LINK_NODE_LOCATION":ln['physical']})
                self.__write_mps_db(path=app_path, macros={"P":app_prefix, "THR_LOADED":"0"})
                if slot == 2:
                  self.__write_header_env(path=app_path, macros={"MPS_LINK_NODE":ln_name})
                  self.__write_iocinfo_env(path=app_path, macros={"AREA":app_prefix.split(':')[1],
                                                                  "LOCATION":app_prefix.split(':')[2],
                                                                  "LOC_IDX":app_prefix.split(':')[2].replace('MP', ''),
                                                                  "C_IDX":app_prefix.split(':')[3]})
                  macros = {"P":'{0}'.format(app_prefix),
                            "MPS_CONFIG_VERSION":'{0}'.format(self.config_version),
                            "MPS_LINK_NODE_TYPE":'{0}'.format(self.__link_node_type_to_number(ln['type'])),
                            "MPS_LINK_NODE_ID":'{0}'.format(ln['lc1_node_id']),
                            "MPS_LINK_NODE_SIOC":'{0}'.format(ln['sioc']),
                            "MPS_CRATE_LOCATION":'{0}'.format(ln['physical']),
                            "MPS_CPU_NAME":'{0}'.format(ln['cpu_name']),
                            "MPS_SHM_NAME":'{0}'.format(ln['shm_name']),
                            "IS_LN":'{0}'.format(1)}
                  self.__write_epics_db(path=app_path,filename='mps.db', template_name="link_node_info.template", macros=macros)
                  for slot2 in range(7):
                    slot2 += 1
                    slot_name = 'Spare'
                    slot_prefix = 'Spare'
                    slot_desc = 'Spare'
                    slot_spare = 1
                    if slot2 in installed:
                      slot_name = ln['slots'][slot2]['type']
                      slot_spare = 0
                      slot_prefix = ln['slots'][slot2]['pv_base']
                      slot_desc = ln['slots'][slot2]['description']
                    macros = {"P":'{0}'.format(app_prefix),
                              "SLOT":'{0}'.format(slot2),
                              "SLOT_NAME":'{0}'.format(slot_name),
                              "SLOT_SPARE":'{0}'.format(slot_spare),
                              "SLOT_PREFIX":'{0}'.format(slot_prefix),
                              "SLOT_DESC":'{0}'.format(slot_desc)}
                    self.__write_link_node_slot_info_db(path=app_path, macros=macros)
                  #If no alalog cards in slot 2, write all channels are not available
                  if ln['type'] == 'Digital':
                    self.__write_app_id_config(path=app_path, macros={"ID":"0","PROC":"3"}) # If there are no analog cards, set ID to invalid
                    for ch in range(0,6):
                      macros = { "P": app_prefix,
                                 "CH":str(ch),
                                 "CH_NAME":"Not Available",
                                 "CH_PVNAME":"None",
                                 "CH_SPARE":"1",
                                 "TYPE":"None"
                               }
                      self.__write_link_node_channel_info_db(path=app_path, macros=macros)
          if ln['analog_slot'] != 2:
            slot = ln['analog_slot']
            app_prefix = ln['slots'][slot]['pv_base']
            app_path = '{}link_node_db/app_db/{}/{:04}/{:02}/'.format(self.dest_path, ln["cpu_name"], ln["crate_id"], slot)
            self.__write_header_env(path=app_path, macros={"MPS_LINK_NODE":ln_name})
            self.__write_iocinfo_env(path=app_path, macros={"AREA":app_prefix.split(':')[1],
                                                            "LOCATION":app_prefix.split(':')[2],
                                                            "LOC_IDX":app_prefix.split(':')[2].replace('MP', ''),
                                                            "C_IDX":app_prefix.split(':')[3]})
            macros = {"P":'{0}'.format(app_prefix),
                      "MPS_CONFIG_VERSION":'{0}'.format(self.config_version),
                      "MPS_LINK_NODE_TYPE":'{0}'.format(ln['type']),
                      "MPS_LINK_NODE_ID":'{0}'.format('AN'),
                      "MPS_LINK_NODE_SIOC":'{0}'.format(ln['sioc']),
                      "MPS_CRATE_LOCATION":'{0}'.format(ln['physical']),
                      "MPS_CPU_NAME":'{0}'.format(ln['cpu_name']),
                      "MPS_SHM_NAME":'{0}'.format(ln['shm_name']),
                      "IS_LN":'{0}'.format(1)}
            self.__write_epics_db(path=app_path,filename='mps.db', template_name="link_node_info.template", macros=macros)
        # ---------------------------#
        # Generate digital application databases and configuration files
        # ---------------------------#
        for app in self.digital_apps:
          app_path = '{}link_node_db/app_db/{}/{:04}/{:02}/'.format(self.dest_path, app["cpu_name"], app["crate_id"], app["slot_number"])
          app_prefix = app['app_prefix']
          self.__write_dig_app_id_confg(path=app_path, macros={"ID":str(app["app_id"])})
          has_virtual = False
          for device in app['devices']:
            for input in device["inputs"]:
              if app["virtual"]:
                has_virtual = True
                if input["bit_position"] >= 32:
                  scan = ".2 second"
                  channel = input['bit_position'] - 32
                  n = input['input_pv']
                  ex = "_IN"
                  if ("WIGG:" in input["input_pv"]):
                    if (channel%2 != 0):
                      ex = "_OUT"
                    n = "{0}{1}".format(input["input_pv"][:-8], ex)                  
                  vmacros = {  "P":input["input_pv"]+'_THR',
                               "R":input["name"],
                               "N":n,
                               "INPV":input["input_pv"],
                               "ALSTATE":str(input["alarm_state"]),
                               "NALSTATE":str(to_bool(not input["alarm_state"])),
                               "ZSV":input["zero_severity"],
                               "OSV":input["one_severity"],
                               "BIT":"{:02d}".format(channel).format,
                               "ZNAM":input["zero_name"],
                               "ONAM":input["one_name"], 
                               "GID":str(app["app_id"]),
                               "SCAN":scan}
                  if (input['name'] == 'WDOG'):
                    self.__write_virtual_wdog_db(path=app_path, macros=vmacros)
                  else:
                    self.__write_virtual_db(path=app_path, macros=vmacros)
              if (self.verbose):
                print(("    Digital Input : {}".format(input["name"])))
          if has_virtual:
            self.__write_mps_virt_db(path=app_path, macros={"P":app_prefix,"HAS_VIRTUAL":"1"})
          else:
            self.__write_mps_virt_db(path=app_path, macros={"P":app_prefix,"HAS_VIRTUAL":"0"})

        # ---------------------------#
        # Generate analog application databases and configuration files
        # ---------------------------#
        for app in self.analog_apps:
            app_path = '{}link_node_db/app_db/{}/{:04}/{:02}/'.format(self.dest_path, app["cpu_name"], app["crate_id"], app["slot_number"])
            app_prefix = app['app_prefix']
            proc = 3
            json_macros = []
            if app['link_node_name'] in ['sioc-bsyh-mp03','sioc-bsys-mp04']:
              proc = 0
            self.__write_app_id_config(path=app_path, macros = {"ID":str(app['app_id']),"PROC":str(proc)})
            self.__write_thresholds_off_config(path=app_path)
            spare_channels = list(range(0,6))
            for device in app['devices']:
              device_prefix = device['prefix']
              for fault in device['faults'].values():
                temp_macros = {}
                temp_macros['fault'] = '{0}:{1}'.format(device['prefix'],fault['name'])
                json_macros.append(temp_macros)
              if device['type_name'] not in self.non_link_node_types:
                macros = { "P": app_prefix,
                           "CH":str(device["channel_index"]),
                           "CH_NAME":device["device_name"],
                           "CH_PVNAME":device_prefix,
                           "CH_SPARE":"0",
                           "TYPE":self.get_analog_type_name(device["type_name"])
                         }
                self.__write_link_node_channel_info_db(path=app_path, macros=macros)
                processing = 0
                ch = device['channel_index']
                if (device["type_name"] == "CBLM"):
                    processing = 1
                if (device["type_name"] == "KICK"):
                    processing = 1
                int0 = device['channel_index']*4
                int1 = device['channel_index']*4 + 1
                macros = { "CH":format(device['channel_index']),
                           "PROC":format(processing),
                           "INT0":format(int0),
                           "INT1":format(int1)
                         }
                self.__write_ana_config(path=app_path, macros=macros)
                spare_channels[device["channel_index"]] = -1
                for integrator in range(4):
                  bsa_slot = integrator*6 + device["channel_index"]
                  inpv = "{0}:ANA_BSA_DATA_{1}".format(app_prefix,bsa_slot)
                  macros = { "P_DEV":device_prefix,
                             "R_DEV":'I{0}_{1}'.format(integrator,self.get_analog_type_name(device["type_name"])),
                             "INT":'I{0}'.format(integrator),
                             "EGU":self.get_app_units(device["type_name"],''),
                             "INPV":inpv
                            }
                  self.__write_analog_db(path=app_path, macros=macros)
                  chan = device["channel_number"]
                  if chan > 2:
                    chan = chan - 3
                  macros_bsa = { "P":"{0}:I{1}_{2}".format(device_prefix,integrator,self.get_analog_type_name(device["type_name"])),
                                 "ATTR":"I{0}_{1}".format(integrator,self.get_analog_type_name(device["type_name"])),
                                 "INP":"{0}:LC1_BSA_B{1}_C{2}_I{3}".format(app_prefix,device["bay_number"],chan,integrator),
                                 "EG":"raw",
                                 "HO":"0",
                                 "LO":"0",
                                 "PR":"0",
                                 "AD":"0"}
                  self.__write_bsa_db(path=app_path, macros=macros_bsa)
                for fault in list(device['faults'].values()):
                  if (device['device_name'] in ['BYD','BYDSH']):
                    inpv = "BEND:DMPH:400:BACT"
                    macros_temp = { "P":device_prefix,
                                    "DESC":device['device_name'],
                                    "INPV":inpv} 
                    self.__write_lc1_dc_db(path=app_path, macros=macros_temp)
                  if (device['device_name'] in ['BYDB','BY1B','BYDSS','BKRCUS','BLRCUS','BRCUSDC','BRCUS1']):
                    inpv = "BEND:DMPS:400:BACT"
                    macros_temp = { "P":device_prefix,
                                    "DESC":device['device_name'],
                                    "INPV":inpv} 
                    self.__write_lc1_dc_db(path=app_path, macros=macros_temp)
                  macros = {  "P":device_prefix,
                              "BAY":format(device["bay_number"]),
                              "APP":self.get_app_type_name(device["type_name"]),
                              "FAULT":'{0}'.format(fault['name']),
                              "FAULT_INDEX":self.get_fault_index(device["type_name"], fault["name"], device["channel_number"]),
                              "DESC":fault["description"],
                              "EGU":self.get_app_units(device["type_name"],fault["name"]),
                              "SLOPE":'{0}'.format(device['slope']),
                              "OFFSET":'{0}'.format(device['offset'])}
                  self.__write_thr_base_db(path=app_path, macros=macros)
                  if (device["type_name"] == "KICK"):
                      if device['device_name'] == 'BYKIK':
                        inpv = "BEND:DMPH:400:BACT"
                        macros_temp = { "P":device_prefix,
                                        "DESC":device['device_name'],
                                        "INPV":inpv,
                                        "BPM":"BPMS:LTUH:960:TMITCUH1H",
                                        "NAME":"DUMP:LTUH:970:MPSPOWER",
                                        "RATE":"IOC:BSY0:MP01:BYKIK_RATEC"} 
                        self.__write_lc1_kick_db(path=app_path, macros=macros_temp)
                      if device['device_name'] == 'BYKIKS':
                        inpv = "BEND:DMPS:400:BACT"
                        macros_temp = { "P":device_prefix,
                                        "DESC":device['device_name'],
                                        "INPV":inpv,
                                        "BPM":"BPMS:LTUS:880:TMITCUS1H",
                                        "NAME":"DUMP:LTUS:972:MPSPOWER",
                                        "RATE":"IOC:BSY0:MP01:BYKIKS_RATEC"}
                        self.__write_lc1_kick_db(path=app_path, macros=macros_temp)
                  # Generate PV for all possible thresholds, even if not defined in database
                  for bit in range(0,7):#fault["bit_positions"]:
                      fault_prefix = "{}_T{}".format(fault["name"], bit)
                      macros["BIT_POSITION"] = str(bit)
                      self.__write_thr_db(path=app_path, macros=macros)
                      if (self.verbose):
                          print(("    Fault prefix : {}".format(fault_prefix)))
            for ch in spare_channels:
                if ch > -1:
                    macros = { "P": app_prefix,
                               "CH":str(ch),
                               "CH_NAME":"Spare",
                               "CH_PVNAME":"None",
                               "CH_SPARE":"1",
                               "TYPE":"Spare"
                               }
                    self.__write_link_node_channel_info_db(path=app_path, macros=macros)
            filename = '{0}/App{1}_checkout.json'.format(self.checkout_path,app['app_id'])
            self.__write_json_file(filename, json_macros)
    def __link_node_type_to_number(self, ln_type):
        if ln_type == 'Digital':
            return 0
        elif ln_type == 'Mixed':
            return 2
        else:
            return 1

    def __write_lc1_info_config(self, link_node):
        """
        Write the LCLS-I link node ID to the configuration file.
        """
        if "lc1_node_id" not in link_node:
            return
        if link_node["lc1_node_id"] == "0":
            ip_str = '0.0.168.192'.format(app["app_id"])
            print('ERROR: Found invalid link node ID (lcls1_id of 0)')
        else:
            ip_str = '{}.0.168.192'.format(link_node["lc1_node_id"])

        ip_address = int(ipaddress.ip_address(ip_str))

        slot = 2
        if "analog_slot" in link_node: 
            slot = link_node["analog_slot"]
        path = '{}link_node_db/app_db/{}/{:04}/{:02}/'.format(self.dest_path, link_node["cpu_name"], link_node["crate_id"], slot)
        mask = 0
        remap_dig = 0
        write =False
        if link_node["type"] == "Digital" or link_node["type"] == "Mixed":
            if "dig_app_id" not in link_node:
              remap_dig = 0
            else:         
              mask = 1
              remap_dig = link_node["dig_app_id"]
              write = True

        bpm_index = 0
        blm_index = 0
        remap_bpm = [0, 0, 0, 0, 0]
        remap_blm = [0, 0, 0, 0, 0]
        for slot_number, slot_info in list(link_node["slots"].items()):
            if slot_number == 2:
                write = True
            if slot_info["type"] == "BPM Card":
                if bpm_index < 5:
                    remap_bpm[bpm_index] = slot_info["app_id"]
                    #mask |= 1 << (bpm_index + 1) # Skip first bit, which is for digital app
                    bpm_index += 1
                else:
                    print(('ERROR: Cannot remap BPM app id {}, all remap slots are used already'.\
                              format(slot_info["app_id"])))
                          
            elif slot_info["type"] == "Generic ADC":
                if blm_index < 5:
                    remap_blm[blm_index] = slot_info["app_id"]
                    mask |= 1 << (blm_index + 1 + 5) # Skip first bit and 5 BPM bits
                    blm_index += 1
                else:
                    print(('ERROR: Cannot remap BLM app id {}, all remap slots are used already'.\
                              format(slot_info["app_id"])))

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
        if write:
            self.__write_fw_config(path=path, template_name="lc1_info.template", macros=macros)

    def generate_cn_db(self):
        """
        Generate the EPICS database for central node from the application data obtained by the
        extract_apps method.

        The files will be written in the destination directory specified from the user (TOP),
        following the following structure:

        <TOP>central_node_db/cn<central_node>/
        """
        # Generate device inputs
        self.generate_digital_db_by_app_id(app_id)
        # Generate analog inputs
        self.generate_analog_db(app_id)
        # Generate beam destinations
        self.generate_dest_db()
        # Generate ignore conditions
        self.generate_condition_db()

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
            macros = { 'P':'{0}'.format(input['input_pv']),
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
              macros = { 'P':"{0}:{1}".format(device['prefix'],fault['states'][idx]),
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
              macros = { 'P':'{0}:{1}_STATE'.format(device['prefix'],fault['states'][idx]),
                         'ID':'{0}'.format(fault["fs_id"][idx]),
                         'DESC':'{0}'.format(fault["fs_desc"][idx]) }
              if app['central_node'] in [0,2]:
                self.__write_fault_state_db(path=self.cn0_path, macros=macros)
                if app['central_node'] in [2]:
                  self.__write_fault_state_db(path=self.cn2_path, macros=macros)
              elif app['central_node'] in [1]:
                self.__write_fault_state_db(path=self.cn1_path, macros=macros)
    
    def generate_displays(self):        
        self.__generate_crate_display()
        self.__generate_input_display()
        self.__generate_group_display()

    def __generate_group_display(self):
      header_height = 50
      footer_height = 51
      embedded_width = 590
      embedded_height = 250
      extra = 10
      for group in range(0,24):
        filtered_link_nodes = {key: val for (key,val) in list(self.link_nodes.items()) if val['group'] == group and val['analog_slot'] == 2}
        last_ln = {key: val for (key,val) in list(filtered_link_nodes.items()) if val['group_link'] == 0}
        last_ln_key = list(last_ln.keys())
        next_to_last_ln = {key: val for (key,val) in list(filtered_link_nodes.items()) if val['group_link'] == last_ln[last_ln_key[0]]['crate_index']}
        last_y = header_height
        rows = 1
        window_width = len(filtered_link_nodes) * embedded_width + extra*2
        if len(next_to_last_ln) > 1:
          last_y = last_y + embedded_height/2
          rows = 2
          window_width = (len(filtered_link_nodes)/2+1) * embedded_width + extra * 2
        last_x = window_width - embedded_width - extra
        window_height = header_height + footer_height + rows*embedded_height
        macros = { 'WIDTH':'{0}'.format(window_width),
                   'HEIGHT':'{0}'.format(window_height),
                   'TITLE':'SC Linac MPS Link Node Group {0}'.format(group) }
        filename = '{0}groups/LinkNodeGroup{1}.ui'.format(self.display_path,group)
        self.__write_group_header(path=filename,macros=macros)
        macros = { 'P':'{0}'.format(last_ln[last_ln_key[0]]['app_prefix']),
                   'CN':'{0}'.format(last_ln[last_ln_key[0]]['cn_prefix']),
                   'AID':'{0}'.format(last_ln[last_ln_key[0]]['dig_app_id']),
                   'SLOT_FILE':'LinkNode{0}_slot.ui'.format(last_ln[last_ln_key[0]]['lc1_node_id']),
                   'P_IN':'{0}'.format(last_ln[last_ln_key[0]]['cn_prefix']),
                   'X':'{0}'.format(last_x),
                   'Y':'{0}'.format(last_y),
                   'PGP':'{0}'.format(last_ln[last_ln_key[0]]['group_link_destination']),
                   'LN':'{0}'.format(last_ln[last_ln_key[0]]['lc1_node_id']),
                   'TYPE':'REM' }
        self.__write_group_embed(path=filename,macros=macros)
        y = header_height
        for key in next_to_last_ln:
          p_in = last_ln[last_ln_key[0]]['app_prefix']
          test_ln = next_to_last_ln[key]
          x = last_x - embedded_width
          macros = { 'P':'{0}'.format(test_ln['app_prefix']),
                     'CN':'{0}'.format(test_ln['cn_prefix']),
                     'AID':'{0}'.format(test_ln['dig_app_id']),
                     'SLOT_FILE':'LinkNode{0}_slot.ui'.format(test_ln['lc1_node_id']),
                     'P_IN':'{0}'.format(p_in),
                     'X':'{0}'.format(x),
                     'Y':'{0}'.format(y),
                     'PGP':'{0}'.format(test_ln['group_link_destination']),
                     'LN':'{0}'.format(test_ln['lc1_node_id']),
                     'TYPE':'LOC' }
          self.__write_group_embed(path=filename,macros=macros)
          more_lns = True
          while more_lns:
            p_in = test_ln['app_prefix']
            link = {k: v for (k,v) in list(filtered_link_nodes.items()) if v['group_link'] == test_ln['crate_index']}
            lk = list(link.keys())
            if len(lk) < 1:
              more_lns = False
              break
            test_ln = link[lk[0]]
            x = x-embedded_width
            macros = { 'P':'{0}'.format(test_ln['app_prefix']),
                       'CN':'{0}'.format(test_ln['cn_prefix']),
                       'AID':'{0}'.format(test_ln['dig_app_id']),
                       'SLOT_FILE':'LinkNode{0}_slot.ui'.format(test_ln['lc1_node_id']),
                       'P_IN':'{0}'.format(p_in),
                       'X':'{0}'.format(x),
                       'Y':'{0}'.format(y),
                       'PGP':'{0}'.format(test_ln['group_link_destination']) ,
                       'LN':'{0}'.format(test_ln['lc1_node_id']),
                       'TYPE':'LOC' }
            self.__write_group_embed(path=filename,macros=macros)
          y = y+embedded_height
        y = window_height-footer_height-1
        self.__write_group_end(path=filename,macros={"Y":"{0}".format(y)})


    def __generate_crate_display(self):
        """
        function to create .json files that feed into pydm template repeater to generate crate profiles
        Macros: SLOT, CN, AID, MPS_PREFIX
        """
        width = 480
        header_height = 40
        header_width = 238
        header_middle = width/2
        widget_height = 20
        height = header_height + widget_height * 8 + 2
        for ln_name, ln in self.link_nodes.items():
          installed = ln['slots'].keys()
          if ln['analog_slot'] == 2:
            macros = {'HEADER_HEIGHT':'{0}'.format(header_height),
                      'HEADER_WIDTH':'{0}'.format(header_width),
                      'HEADER_MIDDLE':'{0}'.format(header_middle),
                      'WIDTH':'{0}'.format(width),
                      'HEIGHT':'{0}'.format(height),
                      'P':'{0}'.format(ln['app_prefix'])}
            filename = '{0}slots/LinkNode{1}_slot.ui'.format(self.display_path,ln['lc1_node_id'])
            self.__write_crate_header(path=filename,macros=macros)
            for slot in range(1,8):
              macros = {}
              y = header_height + slot * widget_height
              x = 5
              if slot in installed:
                type = 'MPS'
                if ln['slots'][slot]['type'] == 'BPM Card':
                  type = 'BPM'
                if ln['slots'][slot]['type'] == 'Analog Card':
                  type = 'BCM/BLEN'  
                if ln['slots'][slot]['type'] == 'Generic ADC':
                  type = 'MPS_AI'
                if ln['slots'][slot]['type'] == 'Digital Card':
                  type = 'MPS_DI'
                if ln['slots'][slot]['type'] == 'LLRF':
                  type = 'LLRF'
                slot_publish = slot
                postfix = 'APP_ID'
                if slot is 1:
                  slot_publish = 'RTM'
                  postfix = 'DIG_APPID_RBV'      
                macros = {'SLOT':'{0}'.format(slot_publish),
                          'CN':'{0}'.format(ln['cn_prefix']),
                          'AID':'{0}'.format(ln['slots'][slot]['app_id']),
                          'MPS_PREFIX':'{0}'.format(ln['slots'][slot]['pv_base']),
                          'TYPE':type,
                          'DESC':'{0}'.format(ln['slots'][slot]['description']),
                          'X':'{0}'.format(x),
                          'Y':'{0}'.format(y),
                          'POSTFIX':postfix}
                self.__write_crate_embed(path=filename,macros=macros)
              else:
                macros = {'SLOT':'{0}'.format(slot),
                          'X':'{0}'.format(x),
                          'Y':'{0}'.format(y)}
                self.__write_empty_slot(path=filename,macros=macros)
            self.__write_crate_footer(path=filename,macros=macros)


    def __generate_input_display(self):
      header_height = 50
      footer_height = 51
      window_width = 950+20
      for app in self.digital_apps:
        filename = '{0}inputs/app_{1}_inputs.ui'.format(self.display_path,app['app_id'])
        input_macros = []
        for device in app['devices']:
          for input in device['inputs']:
            macros = {}
            macros['CRATE'] = '{0}'.format(app['physical'])
            if app['slot_number'] > 2:
              macro['SLOT'] = '{0}'.format(app['slot_number'])
            else:
              macros['SLOT'] = 'RTM'
            macros['CHANNEL'] = input['bit_position']
            macros['DEVICE'] = '{0}'.format(input['input_pv'])
            macros['DEVICE_BYP'] = '{0}'.format(input['input_pv'])
            input_macros.append(macros)
        sorted_macros = sorted(input_macros, key = lambda i: i['CHANNEL'])
        window_height = header_height + footer_height + len(sorted_macros)*20
        header_macros = { "TITLE":"SC Linac Input Status - App ID {0}".format(app['app_id']),
                          "WIDTH":"{0}".format(window_width),
                          "HEIGHT":"{0}".format(window_height) }
        self.__write_cn_input_header(path=filename,macros=header_macros)
        y = header_height
        for macro in sorted_macros:
          macro["Y"] = '{0}'.format(y)
          macro["CHANNEL"] = '{0}'.format(macro["CHANNEL"])
          self.__write_cn_input_embed(path=filename,macros=macro)
          y += 20
        self.__write_cn_input_footer(path=filename,macros={"Y":"{0}".format(y)})
      for app in self.analog_apps:
        input_macros = []
        filename = '{0}inputs/app_{1}_inputs.ui'.format(self.display_path,app['app_id'])
        for device in app['devices']:
          for key in device['faults']:
            for input in range(0,len(device['faults'][key]['bit_positions'])):
              macros = {}
              macros['CRATE'] = '{0}'.format(app['physical'])
              macros['SLOT'] = '{0}'.format(app['slot_number'])
              macros['CHANNEL'] = device['channel_index']
              macros['DEVICE'] = '{0}:{1}'.format(device['prefix'],device['faults'][key]['states'][input])
              macros['DEVICE_BYP'] = '{0}:{1}'.format(device['prefix'],device['faults'][key]['name'])
              input_macros.append(macros)
        sorted_macros = sorted(input_macros, key = lambda i: i['CHANNEL'])
        window_height = header_height + footer_height + len(sorted_macros)*20
        header_macros = { "TITLE":"SC Linac Input Status - App ID {0}".format(app['app_id']),
                          "WIDTH":"{0}".format(window_width),
                          "HEIGHT":"{0}".format(window_height) }
        self.__write_cn_input_header(path=filename,macros=header_macros)
        y = header_height
        for macro in sorted_macros:
          macro["Y"] = '{0}'.format(y)
          macro["CHANNEL"] = '{0}'.format(macro["CHANNEL"])
          self.__write_cn_input_embed(path=filename,macros=macro)
          y += 20
        self.__write_cn_input_footer(path=filename,macros={"Y":"{0}".format(y)})

    def generate_yaml(self):
      mps = MPSConfig(self.database)
      for cn in range(1,4):
        yaml_filename = '{0}/mps_config-cn{1}-{2}.yaml'.format(self.dest_path,cn,self.config_version)
        ioc_tools.dump_db_to_yaml(mps, yaml_filename,cn)
        cmd = "whoami"
        process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
        user_name, error = process.communicate()

        cmd = "md5sum {0}".format(self.database)
        process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
        md5sum_output, error = process.communicate()

        md5sum_tokens = md5sum_output.split()
        file1 = open(yaml_filename,"a")
        file1.write("---\n")
        file1.write("DatabaseInfo:\n")
        file1.write("- source: {0}\n".format(self.database))
        file1.write("  date: {0}\n".format(time.asctime(time.localtime(time.time()))))
        file1.write("  user: {0}\n".format(user_name.strip()))
        file1.write("  md5sum: {0}\n".format(md5sum_tokens[0].strip()))
        file1.close()
      mps.session.close()
                      
          


    def __write_mps_db(self, path, macros):
        """
        Write the base mps records to the application EPICS database file.
        These records will be loaded once per each device.
        """
        self.__write_epics_db(path=path,filename='mps.db', template_name="mps.template", macros=macros)

    def __write_link_node_slot_info_db(self, path, macros):
        self.__write_epics_db(path=path,filename='mps.db', template_name="link_node_slot_info.template", macros=macros)

    def __write_link_node_channel_info_db(self, path, macros):
        self.__write_epics_db(path=path,filename='mps.db', template_name="link_node_channel_info.template", macros=macros)

    def __write_analog_db(self, path, macros):
        """
        Write the records for analog inputs to the application EPICS database file.

        These records will be loaded once per each device.
        """
        self.__write_epics_db(path=path,filename='mps.db', template_name="ln_combined_lc1_analog.template", macros=macros)

    def __write_thr_base_db(self, path, macros):
        """
        Write the base threshold record to the application EPICS database file.
        These records will be loaded once per each fault.
        """
        self.__write_epics_db(path=path,filename='mps.db', template_name="thr_base.template", macros=macros)

    def __write_bsa_db(self, path, macros):
        """
        Write the base threshold record to the application EPICS database file.
        These records will be loaded once per each fault.
        """
        self.__write_epics_db(path=path,filename='mps.db', template_name="bsa.template", macros=macros)

    def __write_lc1_kick_db(self, path, macros):
        """
        Write lcls1 kicker threshold records to the application EPICS database file.
        These records will be loaded once per each fault.
        """
        self.__write_epics_db(path=path,filename='mps.db', template_name="lc1_kick.template", macros=macros)

    def __write_lc1_dc_db(self, path, macros):
        """
        Write lcls1 kicker threshold records to the application EPICS database file.
        These records will be loaded once per each fault.
        """
        self.__write_epics_db(path=path,filename='mps.db', template_name="lc1_bend.template", macros=macros)

    def __write_thr_db(self, path, macros):
        """
        Write the threshold records to the application EPICS database file.
        These records will be load once per each bit in each fault.
        """
        self.__write_epics_db(path=path,filename='mps.db', template_name="thr.template", macros=macros)

    def __write_virtual_db(self, path, macros):
        """
        Write records for digital virtual inputs
        """
        self.__write_epics_db(path=path,filename='mps.db', template_name="virtual.template", macros=macros)

    def __write_virtual_wdog_db(self, path, macros):
        """
        Write records for digital virtual watchdog inputs
        """
        self.__write_epics_db(path=path,filename='mps.db', template_name="watchdog.template", macros=macros)

    def __write_mps_virt_db(self, path, macros):
        """
        Write the base mps records to the application EPICS database file.
        These records will be loaded once per each device.
        """
        self.__write_epics_db(path=path,filename='mps.db', template_name="has_virtual.template", macros=macros)

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

    def __write_header_env(self, path, macros):
        """
        Write the header for the MPS file containing environmental variables.

        This environmental variable will be loaded by all applications.
        """
        self.__write_epics_env(path=path, template_name="header.template", macros=macros)

    def __write_dig_app_id_confg(self, path, macros):
        """
        Write the digital appID configuration section to the application configuration file.
        This configuration will be load by all link nodes.
        """
        self.__write_fw_config(path=path, template_name="dig_app_id.template", macros=macros)

    def __write_app_id_config(self, path, macros):
        """
        Write the appID configuration section to the application configuration file.
        This configuration will be load by all applications.
        """
        self.__write_fw_config(path=path, template_name="app_id.template", macros=macros)

    def __write_thresholds_off_config(self, path):
        """
        Write the Threshold off configuration section to the application configuration file.

        This configuration will be load by all applications.
        """
        self.__write_fw_config(path=path, template_name="thresholds_off.template", macros={})

    def __write_ana_config(self, path, macros):
        """
        Write the analog configuration section to the application configuration file.
        This configuration will be load by all applications.
        """
        self.__write_fw_config(path=path, template_name="analog_settings.template", macros=macros)

    def __write_group_header(self, path, macros):
        self.__write_ui_file(path=path, template_name="ln_group_header.tmpl",macros=macros)

    def __write_group_embed(self, path, macros):
        self.__write_ui_file(path=path, template_name="link_node_group_embedded_display.tmpl",macros=macros)

    def __write_group_end(self, path, macros):
        self.__write_ui_file(path=path, template_name="ln_group_end.tmpl",macros=macros)

    def __write_cn_input_header(self, path,macros):
        self.__write_ui_file(path=path, template_name="cn_input_header.tmpl", macros=macros)

    def __write_cn_input_footer(self, path,macros):
        self.__write_ui_file(path=path, template_name="cn_input_footer.tmpl", macros=macros)

    def __write_cn_input_embed(self, path,macros):
        self.__write_ui_file(path=path, template_name="cn_input_embed.tmpl", macros=macros)

    def __write_crate_header(self, path,macros):
        self.__write_ui_file(path=path, template_name="ln_crate_header.tmpl", macros=macros)

    def __write_crate_footer(self, path,macros):
        self.__write_ui_file(path=path, template_name="ln_crate_footer.tmpl", macros=macros)

    def __write_crate_embed(self,path,macros):
        self.__write_ui_file(path=path, template_name="ln_crate_embed.tmpl", macros=macros)

    def __write_empty_slot(self,path,macros):
        self.__write_ui_file(path=path, template_name="ln_crate_empty.tmpl", macros=macros)

    def __write_ui_file(self, path, template_name, macros):
        template = '{}display/{}'.format(self.template_path, template_name)
        self.__write_file_from_template(file=path,template=template,macros=macros)

    def __write_epics_db(self, path,filename, template_name, macros):
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

    def __write_json_file(self, filename, macros):
        create_dir(filename)
        with open(filename,"w") as file:
          json.dump(macros,file)
       

#################
### Main Body ###
#################

def main(db_file, dest_path, template_path=None, app_id=None, 
         manager_info={'host': 'lcls-daemon2', 'port':1975}, verbose=False):

    if (template_path==None):
        template_path='templates/'

    # Generate the Mps application reader object
    print('Import data...')
    mps_reader = MpsExporter(db_file, template_path, dest_path, app_id, manager_info, verbose)
#    mps_app_reader.pretty_print()
#    exit(0)

    # Print a report of the found applications
    if (verbose):
        mps_app_reader.print_app_data()

    # Generated the application output file
    print("Generate link node databases...")
    mps_reader.generate_ln_epics_db()
    print("Generate central node databases...")
    mps_reader.generate_cn_db()
    print("Generate display files...")
    mps_reader.generate_displays()
    print("Generate yaml...")
    mps_reader.generate_yaml()
    print("Done!")

if __name__ == "__main__":

    # Parse input arguments
    parser = argparse.ArgumentParser(description='Export EPICS databases, displays, alarms, and report')
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
