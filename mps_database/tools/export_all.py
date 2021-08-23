#!/usr/bin/env python

from mps_database.mps_config import MPSConfig, models
from mps_database.tools.mps_names import MpsName
from mps_database import ioc_tools
from sqlalchemy import func, exc
from mps_app_reader import MpsAppReader
from docbook import DocBook
from latex import Latex
from collections import OrderedDict
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
import math

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
        self.report_path = '{}reports/build/'.format(self.dest_path)
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
        for group in range(0,24):
          filen = '{0}scripts/program_ln_fw_group{1}.sh'.format(self.dest_path,group)
          tmpl = '{}scripts/bash_header.template'.format(self.template_path)
          self.__write_file_from_template(file=filen, template=tmpl, macros={})
        filen = '{0}scripts/program_an_fw.sh'.format(self.dest_path)
        tmpl = '{}scripts/bash_header.template'.format(self.template_path)
        self.__write_file_from_template(file=filen, template=tmpl, macros={})
        filen = '{0}scripts/reboot_nodes.sh'.format(self.dest_path)
        tmpl = '{}scripts/bash_header.template'.format(self.template_path)
        self.__write_file_from_template(file=filen, template=tmpl, macros={})
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
                  macros = {'CPU':'{0}'.format(ln['cpu_name']),
                            'SHELF':'{0}'.format(ln['shm_name']),
                            'SLOT':'2'}
                  filen = '{0}scripts/program_ln_fw_group{1}.sh'.format(self.dest_path,ln['group'])
                  tmpl = '{}scripts/program_fw.template'.format(self.template_path)
                  self.__write_file_from_template(file=filen, template=tmpl, macros=macros)
                  filen = '{0}scripts/reboot_nodes.sh'.format(self.dest_path)
                  tmpl = '{}scripts/reboot_nodes.template'.format(self.template_path)
                  self.__write_file_from_template(file=filen, template=tmpl, macros={'LN':'{0}'.format(ln_name)})
                  self.__write_salt_fw(path=app_path,macros={"SLOTS":"0x3e"})
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
            macros = {'CPU':'{0}'.format(ln['cpu_name']),
                      'SHELF':'{0}'.format(ln['shm_name']),
                      'SLOT':'{0}'.format(slot)}
            filen = '{0}scripts/program_an_fw.sh'.format(self.dest_path)
            tmpl = '{}scripts/program_fw.template'.format(self.template_path)
            self.__write_file_from_template(file=filen, template=tmpl, macros=macros)
            filen = '{0}scripts/reboot_nodes.sh'.format(self.dest_path)
            tmpl = '{}scripts/reboot_nodes.template'.format(self.template_path)
            self.__write_file_from_template(file=filen, template=tmpl, macros={'LN':'{0}'.format(ln_name)})
            macros = {"P":'{0}'.format(app_prefix),
                      "MPS_CONFIG_VERSION":'{0}'.format(self.config_version),
                      "MPS_LINK_NODE_TYPE":'{0}'.format(self.__link_node_type_to_number(ln['type'])),
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
            json_macros = {}
            json_macros['prefix'] = app_prefix
            json_macros['cn_prefix'] = app['cn_prefix']
            json_macros['devices'] = []
            json_macros['inputs'] = []
            json_macros['version_prefix'] = self.link_nodes[app['link_node_name']]['app_prefix']
            if app['link_node_name'] in ['sioc-bsyh-mp03','sioc-bsys-mp04']:
              proc = 0
            self.__write_app_id_config(path=app_path, macros = {"ID":str(app['app_id']),"PROC":str(proc)})
            self.__write_thresholds_off_config(path=app_path)
            spare_channels = list(range(0,6))
            for device in app['devices']:
              device_prefix = device['prefix']
              for fault in device['faults'].values():
                json_macros['devices'].append('{0}:{1}'.format(device['prefix'],fault['name']))
                json_macros['inputs'].append('{0}:{1}'.format(device['prefix'],fault['readback']))
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
                  for bit in range(0,8):#fault["bit_positions"]:
                      fault_prefix = "{}_T{}".format(fault["name"], bit)
                      macros["BIT_POSITION"] = str(bit)
                      self.__write_thr_db(path=app_path, macros=macros)
                      if (self.verbose):
                          print(("    Fault prefix : {}".format(fault_prefix)))
                count = 0
                for ch in spare_channels:
                    if ch > -1:
                        count +=1
                        macros = { "P": app_prefix,
                                   "CH":str(ch),
                                   "CH_NAME":"Spare",
                                   "CH_PVNAME":"None",
                                   "CH_SPARE":"1",
                                   "TYPE":"Spare"
                                   }
                        self.__write_link_node_channel_info_db(path=app_path, macros=macros)
              elif device['type_name'] == 'TORO':
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
                  # Generate PV for all possible thresholds, even if not defined in database
                  for bit in range(0,8):#fault["bit_positions"]:
                      fault_prefix = "{}_T{}".format(fault["name"], bit)
                      macros["BIT_POSITION"] = str(bit)
                      self.__write_thr_db(path=app_path, macros=macros)
                      if (self.verbose):
                          print(("    Fault prefix : {}".format(fault_prefix)))
            amc = 0 #Both
            if count >= 3:
              amc = 2
            if count == 6:
              amc = 3
            macros = {"DIS":"{0}".format(amc)}
            self.__write_num_amcs(path=app_path,macros=macros)
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
            if slot_info["type"] == "BPM":
                if bpm_index < 5:
                    remap_bpm[bpm_index] = slot_info["app_id"]
                    #mask |= 1 << (bpm_index + 1) # Skip first bit, which is for digital app
                    bpm_index += 1
                else:
                    print(('ERROR: Cannot remap BPM app id {}, all remap slots are used already'.\
                              format(slot_info["app_id"])))
                          
            elif slot_info["type"] == "MPS Analog":
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

    def generate_condition_db(self):
      macros = {'VERSION':'{0}'.format(self.config_version)}
      self.__write_version_db(path=self.cn0_path, macros=macros)
      self.__write_version_db(path=self.cn1_path, macros=macros)
      self.__write_version_db(path=self.cn2_path, macros=macros) 
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
          ordered_states = sorted(device['logic'],key=lambda x:x['state_number'])
          if len(ordered_states) == 2:
            macros = { 'P':'{0}:{1}_{2}'.format(device['prefix'],fault['name'],'LOGIC'),
                       'DESC':'{0}'.format(fault['description']),
                       'INPA':'{0}_{1}'.format(device['inputs'][0]['input_pv'],'SCMPS'),
                       'ZRST':'{0}'.format(ordered_states[0]['state_name']),
                       'ONST':'{0}'.format(ordered_states[1]['state_name']),
                       'ZRSV':'NO_ALARM',
                       'ONSV':'NO_ALARM' }
            if app['central_node'] in [0,2]:
              self.__write_logic_2_db(path=self.cn0_path, macros=macros)
              if app['central_node'] in [2]:
                self.__write_logic_2_db(path=self.cn2_path, macros=macros)
            elif app['central_node'] in [1]:
              self.__write_logic_2_db(path=self.cn1_path, macros=macros)
            for dest in self.beam_destinations:
              macros = { 'P':'{0}:{1}_{2}_{3}'.format(device['prefix'],fault['name'],dest['name'],'LOGIC'),
                         'DESC':'{0} {1}'.format(fault['description'],dest['name']),
                         'INPA':'{0}_{1}'.format(device['inputs'][0]['input_pv'],'SCMPS'),
                         'ZRST':'{0}'.format(ordered_states[0][dest['name']]['mitigation']),
                         'ONST':'{0}'.format(ordered_states[1][dest['name']]['mitigation']),
                         'ZRSV':'{0}'.format(ordered_states[0][dest['name']]['severity']),
                         'ONSV':'{0}'.format(ordered_states[1][dest['name']]['severity']) }
              if app['central_node'] in [0,2]:
                self.__write_logic_2_db(path=self.cn0_path, macros=macros)
                if app['central_node'] in [2]:
                  self.__write_logic_2_db(path=self.cn2_path, macros=macros)
              elif app['central_node'] in [1]:
                self.__write_logic_2_db(path=self.cn1_path, macros=macros)
          if len(ordered_states) == 4:
            macros = { 'P':'{0}:{1}_{2}'.format(device['prefix'],fault['name'],'LOGIC'),
                       'DESC':'{0}'.format(fault['description']),
                       'INPA':'{0}_{1}'.format(device['inputs'][0]['input_pv'],'SCMPS'),
                       'INPB':'{0}_{1}'.format(device['inputs'][1]['input_pv'],'SCMPS'),
                       'ZRST':'{0}'.format(ordered_states[0]['state_name']),
                       'ONST':'{0}'.format(ordered_states[1]['state_name']),
                       'TWST':'{0}'.format(ordered_states[2]['state_name']),
                       'THST':'{0}'.format(ordered_states[3]['state_name']),
                       'ZRSV':'NO_ALARM',
                       'ONSV':'NO_ALARM',
                       'TWSV':'NO_ALARM',
                       'THSV':'NO_ALARM' }
            if app['central_node'] in [0,2]:
              self.__write_logic_4_db(path=self.cn0_path, macros=macros)
              if app['central_node'] in [2]:
                self.__write_logic_4_db(path=self.cn2_path, macros=macros)
            elif app['central_node'] in [1]:
              self.__write_logic_4_db(path=self.cn1_path, macros=macros)
            for dest in self.beam_destinations:
              macros = { 'P':'{0}:{1}_{2}_{3}'.format(device['prefix'],fault['name'],dest['name'],'LOGIC'),
                         'DESC':'{0} {1}'.format(fault['description'],dest['name']),
                         'INPA':'{0}_{1}'.format(device['inputs'][0]['input_pv'],'SCMPS'),
                         'INPB':'{0}_{1}'.format(device['inputs'][1]['input_pv'],'SCMPS'),
                         'ZRST':'{0}'.format(ordered_states[0][dest['name']]['mitigation']),
                         'ONST':'{0}'.format(ordered_states[1][dest['name']]['mitigation']),
                         'TWST':'{0}'.format(ordered_states[2][dest['name']]['mitigation']),
                         'THST':'{0}'.format(ordered_states[3][dest['name']]['mitigation']),
                         'ZRSV':'{0}'.format(ordered_states[0][dest['name']]['severity']),
                         'ONSV':'{0}'.format(ordered_states[1][dest['name']]['severity']),
                         'TWSV':'{0}'.format(ordered_states[2][dest['name']]['severity']),
                         'THSV':'{0}'.format(ordered_states[3][dest['name']]['severity']) }
              if app['central_node'] in [0,2]:
                self.__write_logic_4_db(path=self.cn0_path, macros=macros)
                if app['central_node'] in [2]:
                  self.__write_logic_4_db(path=self.cn2_path, macros=macros)
              elif app['central_node'] in [1]:
                self.__write_logic_4_db(path=self.cn1_path, macros=macros)
                      

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
            ordered_states = sorted(fault['logic'],key=lambda x:x['state_number'])
            if len(ordered_states) == 2:
              macros = { 'P':'{0}:{1}_{2}'.format(device['prefix'],fault['name'],'LOGIC'),
                         'DESC':'{0}'.format(fault['description']),
                         'INPA':'{0}:{1}_STATE'.format(device['prefix'],fault['states'][0]),
                         'INPB':'{0}:{1}_STATE'.format(device['prefix'],fault['states'][1]),
                         'ZRST':'{0}'.format('OK'),
                         'ONST':'{0}'.format(ordered_states[1]['description']),
                         'TWST':'{0}'.format(ordered_states[0]['description']),
                         'ZRSV':'NO_ALARM',
                         'ONSV':'NO_ALARM',
                         'TWSV':'NO_ALARM' }
              if app['central_node'] in [0,2]:
                self.__write_logic_3_db(path=self.cn0_path, macros=macros)
                if app['central_node'] in [2]:
                  self.__write_logic_3_db(path=self.cn2_path, macros=macros)
              elif app['central_node'] in [1]:
                self.__write_logic_3_db(path=self.cn1_path, macros=macros)
              for dest in self.beam_destinations:
                macros = { 'P':'{0}:{1}_{2}_{3}'.format(device['prefix'],fault['name'],dest['name'],'LOGIC'),
                           'DESC':'{0}'.format(fault['description']),
                           'INPA':'{0}:{1}_STATE'.format(device['prefix'],fault['states'][0]),
                           'INPB':'{0}:{1}_STATE'.format(device['prefix'],fault['states'][1]),
                           'ZRST':'{0}'.format('-'),
                           'ONST':'{0}'.format(ordered_states[1][dest['name']]['mitigation']),
                           'TWST':'{0}'.format(ordered_states[0][dest['name']]['mitigation']),
                           'ZRSV':'NO_ALARM',
                           'ONSV':'{0}'.format(ordered_states[1][dest['name']]['severity']),
                           'TWSV':'{0}'.format(ordered_states[0][dest['name']]['severity']) }
                if app['central_node'] in [0,2]:
                  self.__write_logic_3_db(path=self.cn0_path, macros=macros)
                  if app['central_node'] in [2]:
                    self.__write_logic_3_db(path=self.cn2_path, macros=macros)
                elif app['central_node'] in [1]:
                  self.__write_logic_3_db(path=self.cn1_path, macros=macros)
            if len(ordered_states) == 8:
              macros = { 'P':'{0}:{1}_{2}'.format(device['prefix'],fault['name'],'LOGIC'),
                         'DESC':'{0}'.format(fault['description']),
                         'INPA':'{0}:{1}_STATE'.format(device['prefix'],fault['states'][0]),
                         'INPB':'{0}:{1}_STATE'.format(device['prefix'],fault['states'][1]),
                         'INPC':'{0}:{1}_STATE'.format(device['prefix'],fault['states'][2]),
                         'INPD':'{0}:{1}_STATE'.format(device['prefix'],fault['states'][3]),
                         'INPE':'{0}:{1}_STATE'.format(device['prefix'],fault['states'][4]),
                         'INPF':'{0}:{1}_STATE'.format(device['prefix'],fault['states'][5]),
                         'INPG':'{0}:{1}_STATE'.format(device['prefix'],fault['states'][6]),
                         'INPH':'{0}:{1}_STATE'.format(device['prefix'],fault['states'][7]),
                         'ZRST':'{0}'.format('OK'),
                         'ONST':'{0}'.format(ordered_states[7]['description']),
                         'TWST':'{0}'.format(ordered_states[6]['description']),
                         'THST':'{0}'.format(ordered_states[5]['description']),
                         'FRST':'{0}'.format(ordered_states[4]['description']),
                         'FVST':'{0}'.format(ordered_states[3]['description']),
                         'SXST':'{0}'.format(ordered_states[2]['description']),
                         'SVST':'{0}'.format(ordered_states[1]['description']),
                         'EIST':'{0}'.format(ordered_states[0]['description']),
                         'ZRSV':'NO_ALARM',
                         'ONSV':'NO_ALARM',
                         'TWSV':'NO_ALARM',
                         'THSV':'NO_ALARM',
                         'FRSV':'NO_ALARM',
                         'FVSV':'NO_ALARM',
                         'SXSV':'NO_ALARM',
                         'SVSV':'NO_ALARM',
                         'EISV':'NO_ALARM'}
              if app['central_node'] in [0,2]:
                self.__write_logic_9_db(path=self.cn0_path, macros=macros)
                if app['central_node'] in [2]:
                  self.__write_logic_9_db(path=self.cn2_path, macros=macros)
              elif app['central_node'] in [1]:
                self.__write_logic_9_db(path=self.cn1_path, macros=macros)
              for dest in self.beam_destinations:
                macros = { 'P':'{0}:{1}_{2}_{3}'.format(device['prefix'],fault['name'],dest['name'],'LOGIC'),
                           'DESC':'{0}'.format(fault['description']),
                           'INPA':'{0}:{1}_STATE'.format(device['prefix'],fault['states'][0]),
                           'INPB':'{0}:{1}_STATE'.format(device['prefix'],fault['states'][1]),
                           'INPC':'{0}:{1}_STATE'.format(device['prefix'],fault['states'][2]),
                           'INPD':'{0}:{1}_STATE'.format(device['prefix'],fault['states'][3]),
                           'INPE':'{0}:{1}_STATE'.format(device['prefix'],fault['states'][4]),
                           'INPF':'{0}:{1}_STATE'.format(device['prefix'],fault['states'][5]),
                           'INPG':'{0}:{1}_STATE'.format(device['prefix'],fault['states'][6]),
                           'INPH':'{0}:{1}_STATE'.format(device['prefix'],fault['states'][7]),
                           'ZRST':'{0}'.format('-'),
                           'ONST':'{0}'.format(ordered_states[7][dest['name']]['mitigation']),
                           'TWST':'{0}'.format(ordered_states[6][dest['name']]['mitigation']),
                           'THST':'{0}'.format(ordered_states[5][dest['name']]['mitigation']),
                           'FRST':'{0}'.format(ordered_states[4][dest['name']]['mitigation']),
                           'FVST':'{0}'.format(ordered_states[3][dest['name']]['mitigation']),
                           'SXST':'{0}'.format(ordered_states[2][dest['name']]['mitigation']),
                           'SVST':'{0}'.format(ordered_states[1][dest['name']]['mitigation']),
                           'EIST':'{0}'.format(ordered_states[0][dest['name']]['mitigation']),
                           'ZRSV':'NO_ALARM',
                           'ONSV':'{0}'.format(ordered_states[7][dest['name']]['severity']),
                           'TWSV':'{0}'.format(ordered_states[6][dest['name']]['severity']),
                           'THSV':'{0}'.format(ordered_states[5][dest['name']]['severity']),
                           'FRSV':'{0}'.format(ordered_states[4][dest['name']]['severity']),
                           'FVSV':'{0}'.format(ordered_states[3][dest['name']]['severity']),
                           'SXSV':'{0}'.format(ordered_states[2][dest['name']]['severity']),
                           'SVSV':'{0}'.format(ordered_states[1][dest['name']]['severity']),
                           'EISV':'{0}'.format(ordered_states[0][dest['name']]['severity'])}
                if app['central_node'] in [0,2]:
                  self.__write_logic_9_db(path=self.cn0_path, macros=macros)
                  if app['central_node'] in [2]:
                    self.__write_logic_9_db(path=self.cn2_path, macros=macros)
                elif app['central_node'] in [1]:
                  self.__write_logic_9_db(path=self.cn1_path, macros=macros)

    
    def generate_displays(self):        
        self.__generate_crate_display()
        self.__generate_input_display()
        self.__generate_group_display()
        self.__generate_threshold_display()
        self.__generate_logic_display()

    def __generate_logic_display(self):
      for app in self.analog_apps:
        app_macros = []
        for device in app['devices']:
          for key, fault in list(device['faults'].items()):
            macros = {}
            macros['DEVICE'] = device['device_name']
            macros['FAULT'] = fault['name']
            macros['PV'] = device['prefix']
            macros['STATE'] = '{0}:{1}_{2}'.format(device['prefix'],fault['name'],'LOGIC')
            macros['LINAC'] = '{0}:{1}_{2}_{3}'.format(device['prefix'],fault['name'],'LINAC','LOGIC')
            macros['DIAG0'] = '{0}:{1}_{2}_{3}'.format(device['prefix'],fault['name'],'DIAG0','LOGIC')
            macros['SXU'] = '{0}:{1}_{2}_{3}'.format(device['prefix'],fault['name'],'SXU','LOGIC')
            macros['HXU'] = '{0}:{1}_{2}_{3}'.format(device['prefix'],fault['name'],'HXU','LOGIC')
            app_macros.append(macros)
        filename = '{0}logic/app_{1}_logic.json'.format(self.display_path,app['app_id'])
        self.__write_json_file(filename, app_macros)
      for app in self.digital_apps:
        app_macros = []
        for device in app['devices']:
          for fault in device['faults']:
            macros = {}
            macros['DEVICE'] = device['device_name']
            macros['FAULT'] = fault['name']
            macros['PV'] = device['prefix']
            macros['STATE'] = '{0}:{1}_{2}'.format(device['prefix'],fault['name'],'LOGIC')
            macros['LINAC'] = '{0}:{1}_{2}_{3}'.format(device['prefix'],fault['name'],'LINAC','LOGIC')
            macros['DIAG0'] = '{0}:{1}_{2}_{3}'.format(device['prefix'],fault['name'],'DIAG0','LOGIC')
            macros['SXU'] = '{0}:{1}_{2}_{3}'.format(device['prefix'],fault['name'],'SXU','LOGIC')
            macros['HXU'] = '{0}:{1}_{2}_{3}'.format(device['prefix'],fault['name'],'HXU','LOGIC')
            app_macros.append(macros)
        filename = '{0}logic/app_{1}_logic.json'.format(self.display_path,app['app_id'])
        self.__write_json_file(filename, app_macros)

    def __generate_threshold_display(self):
      for app in self.analog_apps:
        bay0_macros = []
        bay1_macros = []
        for device in app['devices']:
          macros = {}
          macros["P"] = '{0}'.format(app['app_prefix'])
          macros['CH'] = '{0}'.format(device['channel_index'])
          macros['DEVICE_NAME'] = '{0}'.format(device['device_name'])
          macros['PV_PREFIX'] = '{0}'.format(device['prefix'])
          macros['THR0_P'] = False
          macros['THR1_P'] = False
          macros['THR2_P'] = False
          idx = 0
          for f_key in device['faults'].keys():
            new_key = 'THR{0}'.format(int(idx))
            new_vis_key = 'THR{0}_P'.format(int(idx))
            macros[new_key] = '{0}'.format(device['faults'][f_key]['name'])
            macros[new_vis_key] = True
            idx += 1
          if device['bay_number'] == 0:
            bay0_macros.append(macros)
          else:
            bay1_macros.append(macros)
        filename = '{0}thresholds/app{1}_bay0.json'.format(self.display_path,app['app_id'])
        self.__write_json_file(filename, bay0_macros)
        filename = '{0}thresholds/app{1}_bay1.json'.format(self.display_path,app['app_id'])
        self.__write_json_file(filename,bay1_macros)
      for app in self.digital_apps:
        app_macros = []
        for device in app['devices']:
          for input in device['inputs']:
            shift = 0
            visible = False
            byte_pv = '{0}:RTM_DI'.format(app['app_prefix'])
            thr_pv = ''
            if input['bit_position'] < 32:
              shift = input['bit_position']
            if input['name'] == 'HV':
              byte_pv = '{0}_INPUT_RBV'.format(input['input_pv'])
              thr_pv = '{0}_THR'.format(input['input_pv'])
              visible = True
            if input['name'] == 'WDOG':
              byte_pv = '{0}_WDOG_RBV'.format(input['input_pv'])
            macros = {}
            macros['CH'] = '{0}'.format(input['bit_position'])
            macros['PV'] = '{0}'.format(input['input_pv'])
            macros['DISP_PV'] = '{0}'.format(byte_pv)
            macros['THR_PV'] = '{0}'.format(thr_pv)
            macros['SHIFT'] = '{0}'.format(shift)
            macros['VISIBLE'] = '{0}'.format(visible)
            app_macros.append(macros)
        filename = '{0}thresholds/app{1}_rtm.json'.format(self.display_path,app['app_id'])
        self.__write_json_file(filename, app_macros)
      
            

    def __generate_group_display(self):
      header_height = 50
      footer_height = 51
      embedded_width = 590
      embedded_height = 250
      extra = 10
      max_width = 2400
      for group in range(0,24):
        filtered_link_nodes = {key: val for (key,val) in list(self.link_nodes.items()) if val['group'] == group and val['analog_slot'] == 2}
        last_ln = {key: val for (key,val) in list(filtered_link_nodes.items()) if val['group_link'] == 0}
        last_ln_key = list(last_ln.keys())
        next_to_last_ln = {key: val for (key,val) in list(filtered_link_nodes.items()) if val['group_link'] == last_ln[last_ln_key[0]]['crate_index']}
        last_y = header_height
        rows = 1
        window_width = len(filtered_link_nodes) * embedded_width + extra*2
        too_long = False
        fudge = 0
        if len(next_to_last_ln) > 1:
          last_y = last_y + embedded_height/2
          rows = 2
          window_width = int((math.floor(len(filtered_link_nodes)/2)+1) * embedded_width + extra * 2)
        if window_width > max_width:
          last_y = last_y + embedded_height
          rows = 2
          too_long = True
          window_width = int((math.floor(len(filtered_link_nodes)/2)+1) * embedded_width + extra * 2)
          fudge = int(embedded_width / 2)
        window_height = header_height + footer_height + rows*embedded_height
        last_x = window_width - embedded_width - extra - fudge
        macros = { 'WIDTH':'{0}'.format(int(window_width)),
                   'HEIGHT':'{0}'.format(int(window_height)),
                   'TITLE':'SC Linac MPS Link Node Group {0}'.format(group) }
        filename = '{0}groups/LinkNodeGroup{1}.ui'.format(self.display_path,group)
        self.__write_group_header(path=filename,macros=macros)
        macros = { 'P':'{0}'.format(last_ln[last_ln_key[0]]['app_prefix']),
                   'CN':'{0}'.format(last_ln[last_ln_key[0]]['cn_prefix']),
                   'AID':'{0}'.format(last_ln[last_ln_key[0]]['dig_app_id']),
                   'SLOT_FILE':'LinkNode{0}_slot.ui'.format(last_ln[last_ln_key[0]]['lc1_node_id']),
                   'P_IN':'{0}'.format(last_ln[last_ln_key[0]]['cn_prefix']),
                   'X':'{0}'.format(int(last_x)),
                   'Y':'{0}'.format(int(last_y)),
                   'PGP':'{0}'.format(last_ln[last_ln_key[0]]['group_link_destination']),
                   'LN':'{0}'.format(last_ln[last_ln_key[0]]['lc1_node_id']),
                   'TYPE':'REM' }
        self.__write_group_embed(path=filename,macros=macros)
        if rows > 1:
          y = header_height + embedded_height
        else:
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
                     'X':'{0}'.format(int(x)),
                     'Y':'{0}'.format(int(y)),
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
            if x < 0:
              if too_long:
                x = window_width - embedded_width - extra
                y = y-embedded_height
            macros = { 'P':'{0}'.format(test_ln['app_prefix']),
                       'CN':'{0}'.format(test_ln['cn_prefix']),
                       'AID':'{0}'.format(test_ln['dig_app_id']),
                       'SLOT_FILE':'LinkNode{0}_slot.ui'.format(test_ln['lc1_node_id']),
                       'P_IN':'{0}'.format(p_in),
                       'X':'{0}'.format(int(x)),
                       'Y':'{0}'.format(int(y)),
                       'PGP':'{0}'.format(test_ln['group_link_destination']) ,
                       'LN':'{0}'.format(test_ln['lc1_node_id']),
                       'TYPE':'LOC' }
            self.__write_group_embed(path=filename,macros=macros)
          y = y-embedded_height
        y = window_height-footer_height-1
        buttonx = int(window_width/2 - 100)
        buttony = y + 12
        macros = { 'CN':'{0}'.format(last_ln[last_ln_key[0]]['cn_prefix']),
                   'BUTTON_X':'{0}'.format(int(buttonx)),
                   'BUTTON_Y':'{0}'.format(int(buttony)),
                   'Y':'{0}'.format(int(y)) }
        self.__write_group_end(path=filename,macros=macros)


    def __generate_crate_display(self):
        """
        function to create .json files that feed into pydm template repeater to generate crate profiles
        Macros: SLOT, CN, AID, MPS_PREFIX
        """
        width = 480
        header_height = 40
        widget_height = 20
        height = header_height + widget_height * 8 + 5
        for ln_name, ln in self.link_nodes.items():
          installed = ln['slots'].keys()
          if ln['analog_slot'] == 2:
            macros = {'HEADER_HEIGHT':'{0}'.format(int(header_height)),
                      'WIDTH':'{0}'.format(int(width)),
                      'HEIGHT':'{0}'.format(int(height)),
                      'P':'{0}'.format(ln['app_prefix'])}
            filename = '{0}slots/LinkNode{1}_slot.ui'.format(self.display_path,ln['lc1_node_id'])
            self.__write_crate_header(path=filename,macros=macros)
            for slot in range(1,8):
              fn = 'mps_ln_application.ui'
              macros = {}
              y = header_height + slot * widget_height
              x = 5
              if slot in installed:
                type = 'MPS'
                if ln['slots'][slot]['type'] == 'BPM':
                  type = 'BPM'
                if ln['slots'][slot]['type'] == 'BCM/BLEN':
                  type = 'BCM/BLEN'  
                if ln['slots'][slot]['type'] == 'MPS Analog':
                  type = 'MPS_AI'
                if ln['slots'][slot]['type'] == 'MPS Digital':
                  type = 'MPS_DI'
                if ln['slots'][slot]['type'] == 'LLRF':
                  type = 'LLRF'
                if ln['slots'][slot]['type'] == 'Wire Scanner':
                  type = 'WIRE'
                slot_publish = slot
                postfix = 'APP_ID'
                if slot is 1:
                  slot_publish = 'RTM'
                  postfix = 'DIG_APPID_RBV'
                  fn = 'mps_ln_digital.ui'    
                macros = {'SLOT':'{0}'.format(slot_publish),
                          'CRATE':'{0}'.format(ln['physical']),
                          'CN':'{0}'.format(ln['cn_prefix']),
                          'AID':'{0}'.format(ln['slots'][slot]['app_id']),
                          'MPS_PREFIX':'{0}'.format(ln['slots'][slot]['pv_base']),
                          'TYPE':type,
                          'DESC':'{0}'.format(ln['slots'][slot]['description']),
                          'X':'{0}'.format(int(x)),
                          'Y':'{0}'.format(int(y)),
                          'POSTFIX':postfix,
                          'FILENAME':'{0}'.format(fn)}
                self.__write_crate_embed(path=filename,macros=macros)
              else:
                macros = {'SLOT':'{0}'.format(int(slot)),
                          'X':'{0}'.format(int(x)),
                          'Y':'{0}'.format(int(y))}
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
          macro["Y"] = '{0}'.format(int(y))
          macro["CHANNEL"] = '{0}'.format(macro["CHANNEL"])
          self.__write_cn_input_embed(path=filename,macros=macro)
          y += 20
        self.__write_cn_input_footer(path=filename,macros={"Y":"{0}".format(int(y))})

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

    def generate_reports(self):
      create_dir('{0}'.format(self.report_path))
      self.__writeCrateProfiles()
      self.__writeDeviceInputs()
      self.__writeLogicTables()

    def __writeCableReport(self):
      typ = 'cables'
      filename = '{0}/SCMPS_{1}_LogicTables.tex'.format(self.report_path,self.config_version)
      self.latex = Latex(filename)
      self.latex.startDocument('SCMPS Analog Cables Report',self.config_version)
      for group in range(24):
        self.writeLinkNodeGroup(group,typ)
      self.latex.endDocument(self.report_path)

    def __writeLogicTables(self):
      typ = 'logic'
      filename = '{0}/SCMPS_{1}_LogicTables.tex'.format(self.report_path,self.config_version)
      self.latex = Latex(filename)
      self.latex.startDocument('SCMPS Checkout: Logic Tables',self.config_version)
      for group in range(24):
        self.writeLinkNodeGroup(group,typ)
      self.latex.endDocument(self.report_path)      


    def __writeDeviceInputs(self):
      typ = 'inputs'
      filename = '{0}/SCMPS_{1}_DeviceInputs.tex'.format(self.report_path,self.config_version)
      self.latex = Latex(filename)
      self.latex.startDocument('SCMPS Checkout: Device Inputs',self.config_version)
      for group in range(24):
        self.writeLinkNodeGroup(group,typ)
      self.latex.endDocument(self.report_path)      

    def __writeCrateProfiles(self):
      filename = '{0}/SCMPS_{1}_CrateProfiles.tex'.format(self.report_path,self.config_version)
      typ = 'crate'
      self.latex = Latex(filename)
      self.latex.startDocument('SCMPS Checkout: Crate Profiles',self.config_version)
      for group in range(24):
        self.writeLinkNodeGroup(group,typ)
      self.latex.endDocument(self.report_path)

    def writeLinkNodeGroup(self,group,typ):
      filtered_link_nodes = {key: val for (key,val) in list(self.link_nodes.items()) if val['group'] == group and val['analog_slot'] == 2}
      sorted_filtered_link_nodes = OrderedDict(sorted(list(filtered_link_nodes.items()),key=lambda node: node[1]['lc1_node_id']))
      self.latex.startGroup(group)
      for ln in sorted_filtered_link_nodes:
        if typ == 'crate':
          self.latex.startLinkNode(filtered_link_nodes[ln]['lc1_node_id'])
          self.writeCrateProfile(filtered_link_nodes[ln])
        elif typ == 'inputs':
          self.writeAppInput(filtered_link_nodes[ln])
        elif typ == 'logic':
          self.writeAppLogic(filtered_link_nodes[ln])
        elif typ == 'cables':
          self.latex.startLinkNode(filtered_link_nodes[ln]['lc1_node_id'])
          self.writeCables(filtered_link_nodes[ln])

    def writeCables(self,ln):
      installed = list(ln['slots'].keys())
      for slot in range(7):
        channel_lists = []
        if slot in installed:
          app_id = ln['slots'][slot]['app_id']
          for app in self.analog_apps:
            if app['name'] == 'MPS Analog':
              if int(app['app_id']) == int(app_id):
                for device in app['devices']:
                  channel = device['channel_index']
                  name = "{0}".format(device['device_name'])
                  pv = "{0}".format(device['prefix'])
                  cable = device['cable']
                  channel_lists.append([channel,slot,name,pv,cable])     

    def writeAppLogic(self,ln):
      installed = list(ln['slots'].keys())
      for slot in range(7):
        if slot in installed:
          app_id = ln['slots'][slot]['app_id']
          for app in self.digital_apps + self.analog_apps:
            if int(app['app_id']) == int(app_id):
              self.latex.startApplication(app['app_id'],ln['lc1_node_id'])
              self.latex.appCheckoutTable(app['physical'],app['slot_number'])
              if app['type'] == 'analog':
                for device in app['devices']:
                  for key, fault in list(device['faults'].items()):
                      title = fault['description']
                      ordered_states = sorted(fault['logic'],key=lambda x:x['state_number'])
                      out_logic = []
                      out_inputs = []
                      out_state = []
                      out_state.append('OK')
                      out_logic.append(['-','-','-','-'])
                      out_inputs.append('{0}:{1}'.format(device['prefix'],fault['name']))
                      for state in ordered_states:
                          out_state.append(state['state_name'])
                          out_logic.append([state['LINAC']['mitigation'],state['DIAG0']['mitigation'],state['HXU']['mitigation'],state['SXU']['mitigation']])
                      self.latex.writeAnalogLogicTable(out_state,out_logic,out_inputs,title)
              if app['type'] == 'digital':
                for device in app['devices']:
                  for fault in device['faults']:
                    title = fault['description']
                    ordered_states = sorted(device['logic'],key=lambda x:x['state_number'])
                    out_logic = []
                    out_inputs = []
                    out_state = []
                    if len(ordered_states) == 2:
                      out_inputs.append(device['inputs'][0]['input_pv'])
                      for state in ordered_states:
                        out_state.append(state['state_name'])
                        out_logic.append([state['LINAC']['mitigation'],state['DIAG0']['mitigation'],state['HXU']['mitigation'],state['SXU']['mitigation']])
                    if len(ordered_states) == 4:
                      out_inputs.append(device['inputs'][0]['input_pv'])
                      out_inputs.append(device['inputs'][1]['input_pv'])
                      for state in ordered_states:
                        out_state.append(state['state_name'])
                        out_logic.append([state['LINAC']['mitigation'],state['DIAG0']['mitigation'],state['HXU']['mitigation'],state['SXU']['mitigation']])
                    self.latex.writeDigitalLogicTable(out_state,out_logic,out_inputs,title)

    def writeAppInput(self, ln):
      installed = list(ln['slots'].keys())
      for slot in range(7):
        if slot in installed:
          app_id = ln['slots'][slot]['app_id']
          for app in self.digital_apps + self.analog_apps:
            if int(app['app_id']) == int(app_id):
              self.latex.startApplication(app['app_id'],ln['lc1_node_id'])
              self.latex.appCheckoutTable(app['physical'],app['slot_number'])
              self.latex.appCommunicationCheckoutTable()
              if app['type'] == 'analog':
                rows = []
                input_list = []
                for device in app['devices']:
                  for key in device['faults']:
                    for input in range(0,len(device['faults'][key]['bit_positions'])):
                      channel = device['channel_index']
                      device_type = device['type_name']
                      device_name = "{0}".format(device['device_name'])
                      pv = '{0}:{1}'.format(device['prefix'],device['faults'][key]['states'][input])
                      slot_out = app['slot_number']
                      input_list.append([channel,device_name,pv,device_type])
                for element in sorted(input_list, key=lambda x: x[0]):
                  rows.append([element[0],element[1],element[2],element[3]])
                self.latex.writeAppInputs(app['slot_number'],rows)
              if app['type'] == 'digital':
                rows = []
                input_list = []
                for device in app['devices']:
                  for input in device["inputs"]:
                    slot_name = slot
                    channel = input["bit_position"]
                    device_type = device['type_name']
                    name = "{0} {1}".format(device["device_name"], input["name"])
                    if slot is 1:
                      slot_name = 'RTM'
                    if (input["bit_position"] >= 32):
                      pv = input["input_pv"]
                      slot_name = 'SW'
                    else:
                      pv = "{0}:{1}".format(device["prefix"],input["name"])
                    input_list.append([channel,name,pv,device_type])
                for element in sorted(input_list, key = lambda x: x[0]):
                  rows.append([element[0],element[1],element[2],element[3]])
                self.latex.writeAppInputs(app['slot_number'],rows)
              
    def writeCrateProfile(self, ln):
      rack = ln['physical']
      shm = ln['shm_name']
      lc1_id = ln['lc1_node_id']
      rows = []
      for slot in range(7):
        slot_type = 'N/A'
        slot_app_id = 'N/A'
        slot_description = "Not In MPS"
        slot = slot+1
        installed =  list(ln['slots'].keys())
        if slot in installed:
          slot_type = '{0}'.format(ln['slots'][slot]['type'])
          slot_app_id = '{0}'.format(ln['slots'][slot]['app_id'])
          slot_description = '{0}'.format(ln['slots'][slot]['description'])
        if slot == 1:
          slot_report = 'RTM'
        else:
          slot_report = slot
        rows.append([slot_report,slot_app_id,slot_type,slot_description])
      self.latex.crateProfile(lc1_id,shm,rack,rows)    
          
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

    def __write_version_db(self, path, macros):
        """
        Write the digital CN records to the CN EPICS database file.
        These records will be loaded once per each device.
        """
        self.__write_epics_db(path=path,filename='conditions.db',template_name="cn_config_version.template", macros=macros)

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

    def __write_logic_2_db(self, path, macros):
        """
        Write the digital CN records to the CN EPICS database file.
        These records will be loaded once per each device.
        """
        self.__write_epics_db(path=path, filename='logic.db', template_name="cn_logic_2_state.template", macros=macros)

    def __write_logic_3_db(self, path, macros):
        """
        Write the digital CN records to the CN EPICS database file.
        These records will be loaded once per each device.
        """
        self.__write_epics_db(path=path, filename='logic.db', template_name="cn_logic_3_state.template", macros=macros)

    def __write_logic_4_db(self, path, macros):
        """
        Write the digital CN records to the CN EPICS database file.
        These records will be loaded once per each device.
        """
        self.__write_epics_db(path=path, filename='logic.db', template_name="cn_logic_4_state.template", macros=macros)

    def __write_logic_9_db(self, path, macros):
        """
        Write the digital CN records to the CN EPICS database file.
        These records will be loaded once per each device.
        """
        self.__write_epics_db(path=path, filename='logic.db', template_name="cn_logic_9_state.template", macros=macros)

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

    def __write_salt_fw(self,path,macros):
        self.__write_fw_config(path=path, template_name="salt.template", macros=macros)

    def __write_num_amcs(self,path,macros):
        self.__write_fw_config(path=path, template_name="bays_present.template", macros=macros)

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
    print("Generate reports...")
    mps_reader.generate_reports()
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
