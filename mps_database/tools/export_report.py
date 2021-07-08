#!/usr/bin/env python

from mps_database.mps_config import MPSConfig, models
from mps_database.tools.mps_names import MpsName
from sqlalchemy import func, exc
from .mps_app_reader import MpsAppReader
from .docbook import DocBook
from collections import OrderedDict
import os
import sys
import argparse
import subprocess
import time

class Exporter(MpsAppReader):
  databaseFileName = ''
  verbose = False
  cable_report = False
  
  def __init__(self, dbFileName, cable_report):
    self.databaseFileName = dbFileName
    MpsAppReader.__init__(self,db_file=dbFileName,verbose=self.verbose)
    self.cable_report = cable_report
    

  def writeDatabaseInfo(self):
    self.docbook.openSection('Database Information')
    info = self.docbook.getAuthor()
    cols=[{'name':'c1', 'width':'0.3*'},
          {'name':'c2', 'width':'0.7*'}]

    rows=[]
    rows.append(['Generated on', time.asctime(time.localtime(time.time()))])
    rows.append(['Author', '{0}, {1}'.format(info[3], info[2])])
    rows.append(['E-mail', info[1]])
    rows.append(['Username', info[0]])
    rows.append(['Database source', self.databaseFileName])

    cmd = "md5sum {0}".format(self.databaseFileName)
    process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
    md5sum_output, error = process.communicate()
    md5sum_tokens = md5sum_output.split()
    rows.append(['Database file MD5SUM', md5sum_tokens[0].strip()])
    
    self.docbook.table('Database Information', cols, None, rows, 'database_info_table')
    self.docbook.closeSection()

  def writeLinkNodeInformation(self,ln):
    link_node_crate = '{0}'.format(ln['physical'])
    link_node_id = '{0}'.format(ln['lc1_node_id'])
    link_node_cpu = '{0}'.format(ln['cpu_name'])
    link_node_ioc = '{0}'.format(ln['sioc'])
    cols1 = [{'name':'c1', 'width':'0.3*'},
             {'name':'c2', 'width':'0.7*'}]
    rows1 = []
    rows1.append(['Link Node ID:','Link Node {0}'.format(link_node_id)])
    rows1.append(['Link Node Location:',link_node_crate])
    rows1.append(['Link Node Host IOC:',link_node_ioc])
    rows1.append(['Link Node Host CPU:',link_node_cpu])
    ln_header = 'link_node_{0}_info'.format(link_node_id)
    ln_name = 'Link Node {0} Information'.format(link_node_id)
    self.docbook.table(ln_name,cols1,None,rows1,ln_header)

  def writeCrateProfile(self,ln):
    cols = [{'name':'c1', 'width':'0.07*'},
            {'name':'c2', 'width':'0.095*'},
            {'name':'c3', 'width':'0.15*'},
            {'name':'c4', 'width':'0.7*'}]
    
    header=[{'name':'Slot', 'namest':None, 'nameend':None},
            {'name':'App ID', 'namest':None, 'nameend':None},
            {'name':'Type', 'namest':None, 'nameend':None},
            {'name':'Description', 'namest':None, 'nameend':None}] 
    rows = []
    table_name = 'LN {0} Crate Profile: {1}'.format(ln['lc1_node_id'],ln['physical'])
    table_id = 'crate_profile_{0}'.format(ln['physical'])
    for slot in range(7):
      slot_type = 'N/A'
      slot_app_id = 'N/A'
      slot_description = "Not Installed"
      slot = slot+1
      installed =  list(ln['slots'].keys())
      if slot in installed:
        slot_type = '{0}'.format(ln['slots'][slot]['type'])
        slot_app_id = '{0}'.format(ln['slots'][slot]['app_id'])
        slot_description = '{0}'.format(ln['slots'][slot]['description'])
        #temporary = self.writeCables(slot_app_id)
        #if temporary:
        #  cable_rows.extend(temporary)
      rows.append([slot,slot_app_id,slot_type,slot_description])
    self.docbook.table(table_name,cols,header,rows,table_id)

  def writeLinkNode(self, ln):
    cable_rows = []
    cable_cols = [{'name':'c1', 'width':'0.02*'},
            {'name':'c2', 'width':'0.02*'},
            {'name':'c3', 'width':'0.15*'},
            {'name':'c4', 'width':'0.15*'}]
    
    cable_header=[{'name':'Slot', 'namest':None, 'nameend':None},
            {'name':'Ch', 'namest':None, 'nameend':None},
            {'name':'Device', 'namest':None, 'nameend':None},
            {'name':'Cable', 'namest':None, 'nameend':None}]
  
    cable_name = 'Crate {0} Cable Numbers'.format(ln['physical'])
    cable_id = '{0}_cables'.format(ln['physical'])
    section = 'Link Node {0}: {1}'.format(ln['lc1_node_id'], ln['physical'])
    self.docbook.openSection(section)
    if not self.cable_report:
      self.writeLinkNodeInformation(ln)
      self.writeCrateProfile(ln)
      self.writeDigitalInputs(ln)
      self.writeAnalogInputs(ln)
    else:
      self.writeCables(ln)
    self.docbook.closeSection()

  def writePowerClasses(self):
    self.docbook.openSection("Power Classes")
    self.docbook.closeSection()

  def writeDestinations(self):
    self.docbook.openSection("Destinations")
    self.docbook.closeSection()

  def writeLinkNodeGroup(self, ln_group):
    filtered_link_nodes = {key: val for (key,val) in list(self.link_nodes.items()) if val['group'] == ln_group and val['analog_slot'] == 2}
    sorted_filtered_link_nodes = OrderedDict(sorted(list(filtered_link_nodes.items()),key=lambda node: node[1]['lc1_node_id']))
    header = 'Link Node Group {0}'.format(ln_group)
    self.docbook.openSection(header)
    for ln in sorted_filtered_link_nodes:
      self.writeLinkNode(filtered_link_nodes[ln])
    self.docbook.closeSection()

  def writeLinkNodeGroups(self):
    groups = 0
    for (key,val) in list(self.link_nodes.items()):
      if val['group'] > groups:
        groups = val['group']
    for ln_group in range(groups):
      self.writeLinkNodeGroup(ln_group)

  def writeCables(self,ln):
    rows = []
    cols = [{'name':'c1', 'width':'0.02*'},
            {'name':'c2', 'width':'0.02*'},
            {'name':'c3', 'width':'0.15*'},
            {'name':'c4', 'width':'0.15*'},
            {'name':'c5', 'width':'0.15*'}]
    
    header=[{'name':'Slot', 'namest':None, 'nameend':None},
            {'name':'Ch', 'namest':None, 'nameend':None},
            {'name':'Device', 'namest':None, 'nameend':None},
            {'name':'PV', 'namest':None, 'nameend':None},
            {'name':'Cable', 'namest':None, 'nameend':None}]
    table_name = 'LN {0} Cable Report: {0}'.format(ln['lc1_node_id'],ln['physical'])
    table_id = '{0}_cables'.format(ln['physical'])
    installed = list(ln['slots'].keys())
    for slot in range(7):
      channel_lists = []
      if slot in installed:
        app_id = ln['slots'][slot]['app_id']
        for app in self.analog_apps:
          if int(app['app_id']) == int(app_id):
            for device in app['devices']:
              channel = device['channel_index']
              name = "{0}".format(device['device_name'])
              pv = "{0}".format(device['prefix'])
              cable = device['cable']
              channel_lists.append([channel,slot,name,pv,cable])
        for element in sorted(channel_lists, key = lambda x: x[0]):
          rows.append([element[1], element[0], element[2], element[3],element[4]])
    if rows:
      self.docbook.table(table_name,cols,header,rows,table_id)
  
  def writeAnalogInputs(self,ln):
    rows = []
    cols = [{'name':'c1', 'width':'0.02*'},
            {'name':'c2', 'width':'0.02*'},
            {'name':'c3', 'width':'0.02*'},
            {'name':'c4', 'width':'0.03*'},
            {'name':'c5', 'width':'0.15*'},
            {'name':'c6', 'width':'0.15*'},
            {'name':'c7', 'width':'0.03*'},
            {'name':'c8', 'width':'0.02*'}]       
    header=[{'name':'Slot', 'namest':None, 'nameend':None},
            {'name':'ID', 'namest':None, 'nameend':None},
            {'name':'Ch', 'namest':None, 'nameend':None},
            {'name':'Type', 'namest':None, 'nameend':None},
            {'name':'Device Name', 'namest':None, 'nameend':None},
            {'name':'PV Name', 'namest':None, 'nameend':None},
            {'name':'Num Faults', 'namest':None, 'nameend':None},
            {'name':'CN', 'namest':None, 'nameend':None}]
    table_name = 'LN {0} Analog Inputs: {1}'.format(ln['lc1_node_id'],ln['physical'])
    table_id = 'analog_inputs_{0}'.format(ln['physical'])
    installed =  list(ln['slots'].keys())
    for slot in range(7):
      channel_lists = []
      if slot in installed:
        app_id = ln['slots'][slot]['app_id']
        for app in self.analog_apps:
          if int(app['app_id']) == int(app_id):
            for device in app['devices']:
              channel = device['channel_index']
              device_type = device['type_name']
              device_name = "{0} {1}".format(device['device_name'], self.get_analog_type_name(device['type_name']))
              pv = "{0}".format(device['prefix'])
              num_faults = len(device['faults'])
              channel_lists.append([slot,app_id,channel,device_type,device_name, pv, num_faults])
        for element in sorted(channel_lists, key = lambda x: x[2]):
          rows.append([element[0],element[1],element[2],element[3],element[4],element[5],element[6],''])
    if rows:
      self.docbook.table(table_name, cols, header, rows, table_id)

  def writeDigitalInputs(self,ln):
    rows = []
    cols = [{'name':'c1', 'width':'0.021*'},
            {'name':'c2', 'width':'0.02*'},
            {'name':'c3', 'width':'0.02*'},
            {'name':'c4', 'width':'0.03*'},
            {'name':'c5', 'width':'0.15*'},
            {'name':'c6', 'width':'0.15*'},
            {'name':'c7', 'width':'0.015*'}]
    header=[{'name':'Slot', 'namest':None, 'nameend':None},
            {'name':'ID','namest':None,'nameend':None},
            {'name':'Ch', 'namest':None, 'nameend':None},
            {'name':'Type', 'namest':None, 'nameend':None},
            {'name':'Name', 'namest':None, 'nameend':None},
            {'name':'PV', 'namest':None, 'nameend':None},
            {'name':'CN', 'namest':None, 'nameend':None}]
    table_name = 'LN {0} Digital Inputs: {1}'.format(ln['lc1_node_id'],ln['physical'])
    table_id = 'digital_inputs_{0}'.format(ln['physical'])
    installed =  list(ln['slots'].keys())
    for slot in range(7):
      channel_lists = []
      if slot in installed:
        app_id = ln['slots'][slot]['app_id']
        for app in self.digital_apps:
          if int(app['app_id']) == int(app_id):
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
                channel_lists.append([slot_name,app_id,channel,device_type,name,pv])
        for element in sorted(channel_lists, key = lambda x: x[2]):
          rows.append([element[0],element[1],element[2],element[3],element[4],element[5],''])
    if rows:
      self.docbook.table(table_name,cols,header,rows,table_id)  

  def exportDocBook(self, filename, databaseName):
    fname = 'Input'
    lname = 'Report'
    if self.cable_report:
      fname = 'Cable'
      lname = 'Report'
    self.docbook = DocBook(filename)
    self.docbook.startDocument()
    info = self.docbook.getAuthor()
    self.docbook.writeHeader('Superconducting Linac Machine Protection System', fname, lname)
    self.writeDatabaseInfo()
    if not self.cable_report:
      self.writePowerClasses()
      self.writeDestinations()
    self.writeLinkNodeGroups()
    self.docbook.writeFooter()
    suffix = ''
    self.docbook.exportHtml(suffix)
    self.docbook.exportPdf(suffix)

# ------ Main -----

parser = argparse.ArgumentParser(description='Generate documentation for MPS database')
parser.add_argument('database', metavar='db', type=file, nargs=1,help='database file name (e.g. mps_gun.db)')
parser.add_argument('--output', metavar='output', type=str, nargs='?', 
                    help='directory where the documentation is generated')
parser.add_argument('--cables', dest='cables', action='store_true', default=False,
                    help="Generate cable report")
args = parser.parse_args()

output_dir = '.'
if args.output:
  output_dir = args.output
  if (not os.path.isdir(output_dir)):
    print('ERROR: Invalid output directory {0}'.format(output_dir))
    exit(-1)

doc_name = args.database[0].name.split('/')[len(args.database[0].name.split('/'))-1].split('.')[0]
if (args.cables):
  filename = '{0}/{1}-cables.xml'.format(output_dir,doc_name)
else:
  filename = '{0}/{1}.xml'.format(output_dir,doc_name)

e = Exporter(args.database[0].name, args.cables)
e.exportDocBook(filename, doc_name)

