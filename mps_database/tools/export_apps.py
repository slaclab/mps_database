#!/usr/bin/env python
from mps_database.mps_config import MPSConfig, models, runtime
from sqlalchemy import MetaData
from mps_database.tools.mps_names import MpsName
from mps_database.tools.mps_reader import MpsReader, MpsDbReader
from mps_database.tools.export_device import ExportDevice
import datetime
import argparse
import time
import yaml
import os
import sys

class ExportApplication(MpsReader):

  def __init__(self, db_file, template_path, dest_path,clean, verbose):
    MpsReader.__init__(self,db_file=db_file,dest_path=dest_path,template_path=template_path,clean=clean,verbose=verbose)
    self.export_device = ExportDevice(db_file,template_path,dest_path,False,verbose)
    self.verbose = verbose

  def export(self,mps_db_session,card,inputDisplay):
    app_path = self.get_app_path(card.link_node,card.slot_number)
    proc = 3
    if card.link_node.get_name() in ['sioc-bsyh-mp03','sioc-bsys-mp04']:
      proc = 0
    if card.type.name == "MPS Analog":
      self.__write_thresholds_off_config(path=app_path)
      self.__write_app_id_config(path=app_path, macros={"ID":str(card.number)})
      self.__write_processing_config(path=app_path,macros={"PROC":str(proc)})
      amc = 0 #Both
      if len(card.analog_channels) >= 3:
        amc = 2
      if len(card.analog_channels) == 6:
        amc = 3
      macros = {"DIS":"{0}".format(amc)}
      self.__write_num_amcs(path=app_path,macros=macros)
      if card.slot_number != 2:
        self.__write_mps_db(path=app_path, macros={"P":card.get_pv_name(), "THR_LOADED":"0"})
        self.__write_prefix_env(path=app_path, macros={"P":card.get_pv_name(),
                                                       "MPS_DB_VERSION":self.config_version,
                                                       "DATE":datetime.datetime.now().strftime('%Y.%m.%d-%H:%M:%S'),
                                                       "MPS_LINK_NODE_LOCATION":card.link_node.crate.location})
    else:
      self.__write_mps_db(path=app_path, macros={"P":card.get_pv_name(), "THR_LOADED":"0"})
      self.__write_prefix_env(path=app_path, macros={"P":card.get_pv_name(),
                                                     "MPS_DB_VERSION":self.config_version,
                                                     "DATE":datetime.datetime.now().strftime('%Y.%m.%d-%H:%M:%S'),
                                                     "MPS_LINK_NODE_LOCATION":card.link_node.crate.location})
      if card.type.name == "MPS Digital":
        self.__write_dig_app_id_config(path=app_path, macros={"ID":str(card.number)})
      else:
        self.__write_app_id_config(path=app_path, macros={"ID":str(card.number)})
        self.__write_thresholds_off_config(path=app_path)
    self.write_cn_app_id(card)
    inputDisplay.reset_digital_ln_macros()
    inputDisplay.reset_analog_macros()
    self.export_device.export(mps_db_session,card,inputDisplay)
    if len(inputDisplay.get_digital_ln_macros()) > 0:
      filename = '{0}thresholds/app{1}_rtm.json'.format(self.display_path,card.number)
      self.write_json_file(filename, inputDisplay.get_digital_ln_macros())
    if len(inputDisplay.get_analog_macros(0)) > 0:
      filename = '{0}thresholds/app{1}_bay0.json'.format(self.display_path,card.number)
      self.write_json_file(filename, inputDisplay.get_analog_macros(0))     
    if len(inputDisplay.get_analog_macros(1)) > 0:
      filename = '{0}thresholds/app{1}_bay1.json'.format(self.display_path,card.number)
      self.write_json_file(filename, inputDisplay.get_analog_macros(1)) 

  def write_cn_app_id(self,card):
    macros = { 'APP_ID':'{0}'.format(card.number),
               'TYPE':'{0}'.format(card.name),
               'LOCA':'{0}'.format(card.link_node.crate.location),
               'SLOT':'{0}'.format(card.slot_number),
               'ID':'{0}'.format(card.id) }
    self.write_cn_app_db(card.link_node,macros=macros)

  def write_cn_app_db(self,ln,macros):
    if ln.get_cn1_prefix() == 'SIOC:SYS0:MP01':
      self.write_epics_db(path=self.cn0_path,filename='apps.db',template_name="cn_app_timeout.template", macros=macros)
    elif ln.get_cn1_prefix() == 'SIOC:SYS0:MP02':   
      self.write_epics_db(path=self.cn1_path,filename='apps.db',template_name="cn_app_timeout.template", macros=macros)
    if ln.get_cn2_prefix() == 'SIOC:SYS0:MP03':
      self.write_epics_db(path=self.cn2_path,filename='apps.db',template_name="cn_app_timeout.template", macros=macros)

        

  def __write_prefix_env(self, path, macros):
      """
      Write the  mps PV name prefix environmental variable file.
      This environmental variable will be loaded by all applications.
      """
      self.write_epics_env(path=path, template_name="prefix.template", macros=macros)

  def __write_mps_db(self, path, macros):
      """
      Write the base mps records to the application EPICS database file.
      These records will be loaded once per each device.
      """
      self.write_epics_db(path=path,filename='mps.db', template_name="mps.template", macros=macros)
  
  def __write_thresholds_off_config(self, path):
      """
      Write the Threshold off configuration section to the application configuration file.

      This configuration will be load by all applications.
      """
      self.write_fw_config(path=path, template_name="thresholds_off.template", macros={})

  def __write_app_id_config(self, path, macros):
      """
      Write the appID configuration section to the application configuration file.
      This configuration will be load by all applications.
      """
      self.write_fw_config(path=path, template_name="app_id.template", macros=macros)

  def __write_processing_config(self, path, macros):
      """
      Write the appID configuration section to the application configuration file.
      This configuration will be load by all applications.
      """
      self.write_fw_config(path=path, template_name="processing.template", macros=macros)

  def __write_dig_app_id_config(self, path, macros):
      """
      Write the digital appID configuration section to the application configuration file.
      This configuration will be load by all link nodes.
      """
      self.write_fw_config(path=path, template_name="dig_app_id.template", macros=macros)

  def __write_thresholds_off_config(self, path):
      """
      Write the Threshold off configuration section to the application configuration file.
      This configuration will be load by all applications.
      """
      self.write_fw_config(path=path, template_name="thresholds_off.template", macros={})

  def __write_num_amcs(self,path,macros):
      self.write_fw_config(path=path, template_name="bays_present.template", macros=macros)
