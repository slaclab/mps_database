#!/usr/bin/env python
from mps_database.mps_config import MPSConfig, models, runtime
from sqlalchemy import MetaData
from mps_database.tools.mps_names import MpsName
import argparse
import time
import yaml
import os
import sys

class DatabaseImporter:
  conf = None # MPSConfig
  session = None
  beam_destinations = []
  verbose = False
  database_file_name = None

  def __init__(self, file_name, verbose, clear_all=False):
    self.database_file_name = file_name
    self.conf = MPSConfig(file_name)
    if (clear_all):
      self.conf.clear_all()
    self.session = self.conf.session
    self.session.autoflush=False
#    self.session.autoflush=True
    self.verbose = verbose
    self.mps_names = MpsName(self.session)
    self.cn1 = [8,9,10,11,12,13,14]
    self.cn2 = [15,16,17,18,19,20,21,22,23,24]
    self.cn3 = [0,1,2,3,4,5,6,7]

  def __del__(self):
    self.session.commit()

# linac = models.BeamDestination(name="LINAC", description="Linac destination", destination_mask=0x01)
  def add_beam_destinations(self, file_name):
    f = open(file_name)
    line = f.readline().strip()
    fields=[]
    for field in line.split(','):
      fields.append(str(field).lower())
    while line:
      destination_info={}
      line = f.readline().strip()
      if line:
        field_index = 0
        for property in line.split(','):
          destination_info[fields[field_index]]=property
          field_index = field_index + 1

        self.beam_destinations.append(destination_info['name'])
        beam_destination = models.BeamDestination(name=destination_info['name'],
                                                  description=destination_info['description'],
                                                  destination_mask=int(destination_info['destination_mask']))

        self.session.add(beam_destination)
    self.session.commit()
    f.close()

  def add_beam_classes(self, file_name):
    f = open(file_name)
    line = f.readline().strip()
    fields=[]
    for field in line.split(','):
      fields.append(str(field).lower())
    while line:
      class_info={}
      line = f.readline().strip()
      if line:
        field_index = 0
        for property in line.split(','):
          class_info[fields[field_index]]=property
          field_index = field_index + 1
        beam_class = models.BeamClass(number=class_info['number'],
                                      name=class_info['name'],
                                      description=class_info['description'],
                                      integration_window=int(class_info['integration_window']),
                                      total_charge=int(class_info['total_charge']),
                                      min_period=int(class_info['min_period']))

        self.session.add(beam_class)
    self.session.commit()
    f.close()

  def add_crates(self, file_name):
    if self.verbose:
      print(("Adding crates... {0}".format(file_name)))
    f = open(file_name)

    line = f.readline().strip()
    fields=[]
    for field in line.split(','):
      fields.append(str(field).lower())

    while line:
      crate_info={}
      line = f.readline().strip()

      if line:
        field_index = 0
        for property in line.split(','):
          crate_info[fields[field_index]]=property
          field_index = field_index + 1

        locations=[crate_info['ln_location']]
        slots=[crate_info['ln_slot']]
        lcls1_ids=[crate_info['lcls1_id']]

        if (';' in crate_info['ln_location'] and
            ';' in crate_info['ln_slot'] and
            ';' in crate_info['lcls1_id']):
          locations=crate_info['ln_location'].split(';')
          slots=crate_info['ln_slot'].split(';')
          lcls1_ids=crate_info['lcls1_id'].split(';')

        crate = models.Crate(crate_id=crate_info['crate_id'],
                             num_slots=crate_info['num_slots'],
                             shelf_number=int(crate_info['shelf_number']),
                             location=crate_info['location'],
                             rack=crate_info['rack'],
                             elevation=crate_info['elevation'],
                             sector=crate_info['sector'])
#                             link_node=slot2_ln)

        self.session.add(crate)

        for l,s,i in zip(locations,slots,lcls1_ids):
          lcls1_id = 0
          ln_group = self.find_group(crate_info['group'])
          if s == '2':
            ln = models.LinkNode(area=crate_info['ln_area'], location=l,
                                 cpu=crate_info['cpu_name'], ln_type=crate_info['ln_type'],
                                 group=crate_info['group'], group_link=crate_info['group_link'],
                                 group_link_destination=crate_info['group_link_destination'],
                                 group_drawing=crate_info['network_drawing'],
                                 slot_number=s, lcls1_id=i, crate=crate)
            self.session.add(ln)
            ln_group.link_nodes.append(ln)
          if (s == '2'):
            slot2_ln = ln
        self.session.commit()
  
  def find_group(self,gn):
    groups = self.session.query(models.LinkNodeGroup).filter(models.LinkNodeGroup.number == int(gn)).all()
    if len(groups) > 1:
      print("ERROR: Too many groups {0}".format(gn))
      return
    if len(groups) < 1:
      # Create a new group
      if int(gn) in self.cn1:
        cn = 'SIOC:SYS0:MP01'
      elif int(gn) in self.cn2:
        cn = 'SIOC:SYS0:MP02'
      elif int(gn) in self.cn3:
        cn = 'SIOC:SYS0:MP03'
      group = models.LinkNodeGroup(number=int(gn),central_node=cn)
      self.session.add(group)
      self.session.commit()
      return group
    if len(groups) == 1:
      return groups[0]
    return None                                   

  def add_app_types(self, file_name):
    if self.verbose:
      print(("Adding Application Types... {0}".format(file_name)))
    f = open(file_name)
    line = f.readline().strip()
    fields=[]
    for field in line.split(','):
      fields.append(str(field).lower())
    while line:
      app_type_info={}
      line = f.readline().strip()
      if line:
        field_index = 0
        for property in line.split(','):
          app_type_info[fields[field_index]]=property
          field_index = field_index + 1
#        print app_type_info
        app_type = models.ApplicationType(number=app_type_info['number'],
                                          name=app_type_info['name'],
                                          digital_channel_count=app_type_info['digital_channel_count'],
                                          digital_channel_size=app_type_info['digital_channel_size'],
                                          digital_out_channel_count=app_type_info['digital_out_channel_count'],
                                          digital_out_channel_size=app_type_info['digital_out_channel_size'],
                                          analog_channel_count=app_type_info['analog_channel_count'],
                                          analog_channel_size=app_type_info['analog_channel_size'])
        self.session.add(app_type)      
    self.session.commit()
    f.close()
    if self.verbose:
      print(("Done: Adding Application Types... {0}".format(file_name)))

  def find_app_link_node(self, crate, slot):
    """
    Return the link node that connects to the specified slot for the crate
    """
    slots = []
    for ln in crate.link_nodes:
      slots.append(ln.slot_number)

    link_node = None
    for ln in crate.link_nodes:
      if (slot == ln.slot_number):
        return ln
      elif (ln.slot_number == 2 and not slot in slots):
        return ln
      elif (not slot in slots and slot == ln.slot_number):
        return ln

    return link_node

  def add_cards(self, file_name):
    if self.verbose:
      print(("Adding Application Cards... {0}".format(file_name)))
    f = open(file_name)
    line = f.readline().strip()
    fields=[]
    for field in line.split(','):
      fields.append(str(field).lower())
    while line:
      app_card_info={}
      line = f.readline().strip()
      if line:
        field_index = 0
        for property in line.split(','):
          app_card_info[fields[field_index]]=property
          field_index = field_index + 1
        if app_card_info['number'] != app_card_info['global_id']:
          print("WARNING: App has number {0} and global_id {1}.  These should be the same!".format(app_card_info['number'],app_card_info['global_id']))
        app_card_type = self.session.query(models.ApplicationType).\
            filter(models.ApplicationType.name==app_card_info['type']).one()
        crate = self.session.query(models.Crate).\
            filter(models.Crate.location==app_card_info['crate']).one()
        link_nodes = self.session.query(models.LinkNode).filter(models.LinkNode.crate == crate).all()
        for node in link_nodes:
          if node.slot_number == 2:
            link_node = node
        installed = self.session.query(models.ApplicationCard).filter(models.ApplicationCard.number == app_card_info['number']).all()
        if len(installed) > 0:
          print('INFO: App {0} already in database!'.format(app_card_info['number']))
        else:
          app_card = models.ApplicationCard(name=app_card_info['name'],
                                            number=int(app_card_info['number']),
                                            area=app_card_info['area'],
                                            type=app_card_type,
                                            slot_number=int(app_card_info['slot']),
                                            amc=int(app_card_info['amc']),
                                            global_id=int(app_card_info['number']),
                                            description=app_card_info['description'],
                                            location=app_card_info['location'],
                                            link_node=link_node)
          self.session.add(app_card)
          crate.cards.append(app_card)
    self.session.commit()    
    f.close() 
    if self.verbose:
      print(("Done: Adding Application Cards... {0}".format(file_name)))

### MAIN

parser = argparse.ArgumentParser(description='Create MPS database')
parser.add_argument('-v',action='store_true',default=False,dest='verbose',help='Verbose output')
parser.add_argument('-n',action='store_true',default=False,dest='new_db',help='Create new db')
parser.add_argument('-c',action='store_true',default=False,dest='crate',help='Add Crate')
parser.add_argument('-t',action='store_true',default=False,dest='app_type',help='Add App Type')
parser.add_argument('-a',action='store_true',default=False,dest='app_card',help='Add App Card')
parser.add_argument('-d',action='store_true',default=False,dest='dest',help='Add Destination')
parser.add_argument('-b',action='store_true',default=False,dest='bc',help='Add Beam Class')
parser.add_argument('--db',metavar='database',required=True,help='MPS sqlite database file')
parser.add_argument('--file',metavar='csvFile',required=True,help='relative path to CSV file to add')
args = parser.parse_args()

verbose=False
if args.verbose:
  verbose=True

new_db=False
if args.new_db:
  new_db = True

db_file=args.db

csv_file = args.file

if new_db:
  importer = DatabaseImporter(db_file, verbose,True)
else:
  importer = DatabaseImporter(db_file,verbose,False)

crate=False
if args.crate:
  importer.add_crates(args.file)

app_type=False
if args.app_type:
  importer.add_app_types(args.file)

app_card=False
if args.app_card:
  importer.add_cards(args.file)

dest=False
if args.dest:
  importer.add_beam_destinations(args.file)

bc=False
if args.bc:
  importer.add_beam_classes(args.file)
