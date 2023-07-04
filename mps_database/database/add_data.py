#!/usr/bin/env python
from mps_database.mps_config import MPSConfig,models
from sqlalchemy import MetaData
import argparse
import json

"""
add_data.py

Adds data to the mps_database, depending on what is in the json file

arguments:
  -v: verbose output
  -n: creates a new database (erases all existing data).  Use with care
  --db: relative path to mps_database to make changes to
  --file: relative path to json file with desired new data
"""

class AddDbData:
"""
class AddDbData:

Adds data to the mps_database, depending on what is in the json file

inputs:
  file_name: filename of the mps_database
  verbose: verbose output
  clear_all: erase all data in the mps_database and start over
"""
  def __init__(self, file_name, verbose,clear_all=False):
    self.verbose = verbose
    self.database_file_name = file_name
    self.conf = MPSConfig(file_name)
    self.session = self.conf.session
    self.session.autoflush=False
    self.dests = ['MECH_SHUTTER','SC_DIAG0','SC_BSYD','SC_HXR','SC_SXR','SC_LESA','LASER_HTR','LASER']
    if (clear_all):
      self.conf.clear_all()

  def _load_json_file(self,json_file):
  """
  _load_json_file:
    return object to data from json file
  inputs:
    json_file: relative path to json file
  """
    with open(json_file,'r') as session_file:
      return json.load(session_file)

  def find_crate(self,node,dont_add=False):
  """
  find_crate:
   search in mps_database for the crate defined in node['crate'] e.g. L2KA00-1521
    If found, return mps_database object.  If not found:
      if dont_add is True, return None
      if dont_add is False, add a new crate with properties in node
  inputs:
    node: datastructure with information about this crate:
      node['crate'] = crate location e.g. L2KA00-1521
      node['crate_id] = crate ID, in current design this is 1 or 101
      node['area'] = control system area where this crate is
      node['node'] = control system device e.g. SP01
  """
    elevation = int(node['crate'].split('-')[1][-2::])
    rack = node['crate'].split('-')[1][0:-2]
    crates = self.session.query(models.Crate).filter(models.Crate.location == node['crate']).all()
    found_crate=True
    if len(crates)>0:
      found_crate = False
      return crates[0]
    if dont_add:
      print("ERROR: Crate {0} not found".format(node['crate']))
      return None
    if found_crate:
      if self.verbose:
        print("INFO: Adding new crate {0}".format(node['crate']))
      new_crate = models.Crate(num_slots=7,
                               crate_id=node['crate_id'],
                               location=node['crate'],
                               rack=rack,
                               elevation=elevation,
                               area=node['area'],
                               node=node['node'])
      self.session.add(new_crate)
      return new_crate

  def find_card(self,num):
  """
  find_card:
   search in mps_database for the card defined with appid (global id) of num
    If found, return mps_database object.  
    If more than one card found, print error and return None
    If no cards found, print error and return None
  inputs:
    card: int with card number (appid or global id)
  """
    num = int(num)
    cards = self.session.query(models.ApplicationCard).filter(models.ApplicationCard.number == num).all()
    if len(cards) < 1:
      print("ERROR: No application card found for AppID {0}".format(num))
      return None
    if len(cards) > 1:
      print("ERROR: Too many application cards found for AppID {0}".format(num))
      return None
    return cards[0]

  def find_group(self,group):
  """
  find_group:
   search in mps_database for the group defined with number group
    If found, return mps_database object.  
    If more than one group found, print error and return None
    If no group found, add it to the database and attach it to a central node
  inputs:
    group: int with group number
  """
    group = int(group)
    groups = self.session.query(models.LinkNodeGroup).filter(models.LinkNodeGroup.number == group).all()
    if len(groups) > 1:
      print("ERROR: Too many groups with this number")
      return None
    if len(groups) == 1:
      return groups[0]
    else:
      if self.verbose:
        print("INFO: Adding new Link Node Group {0}".format(group))
      cn1 = [8,9,10,11,12,13,14]
      cn2 = [15,16,17,18,19,20,21,22,23,24]
      cn3 = [0,1,2,3,4,5,6,7]
      if group in cn1:
        cn = self.session.query(models.CentralNode).filter(models.CentralNode.location=='MP01').one()
      elif group in cn2:
        cn = self.session.query(models.CentralNode).filter(models.CentralNode.location=='MP02').one()
      elif group in cn3:
        cn = self.session.query(models.CentralNode).filter(models.CentralNode.location=='MP03').one()
      else:
        print("ERROR: Central Node not found")
        return None
      new_group = models.LinkNodeGroup(number=group,central_node=cn)
      self.session.add(new_group)
      cn.groups.append(new_group)
      return new_group

  def add_link_node(self,json_file):
  """
  add_link_node:
   Add a link node to the mps_database.  Link it to correct crate and correct group
  inputs:
    json_file: json file defined in main.
  """
    properties = self._load_json_file(json_file)
    if 'link_nodes' in properties:
      for ln in properties['link_nodes']:
        existing_link_nodes = self.session.query(models.LinkNode).filter(models.LinkNode.lnid == ln['lnid']).all()
        if len(existing_link_nodes) > 0:
          print("WARNING: Link Node {0} already exists!".format(ln['lnid']))
        else:
          if self.verbose:
            print("INFO: Adding new link node {0}".format(ln['lnid']))
          location = ln['location']
          crate = self.find_crate(ln)
          group=self.find_group(ln['group'])
          link_node = models.LinkNode(location=location,
                                         group_link=ln['group_link'],
                                         rx_pgp=ln['rx_pgp'],
                                         ln_type=ln['ln_type'],
                                         lnid=ln['lnid'],
                                         crate=crate,
                                         group=group)
          self.session.add(link_node)
          crate.link_node.append(link_node)
          self.session.commit()

  def add_central_node(self,json_file):
  """
  add_central_node:
   Add a central node to the mps_database.  Link it to correct crate and correct groups
  inputs:
    json_file: json file defined in main.
  """
    properties = self._load_json_file(json_file)
    if 'central_nodes' in properties:
      for cn in properties['central_nodes']:
        existing_central_nodes = self.session.query(models.CentralNode).filter(models.CentralNode.location == cn['location']).all()
        if len(existing_central_nodes) > 0:
          print("Warning: Central Node {0} already exists!".format(cn['location']))
        else:
          if self.verbose:
            print("INFO: Adding central node {0}".format(cn['location']))
          area = cn['area']
          location = cn['location']
          slot = int(cn['slot'])
          crate = self.find_crate(cn)
          central_node = models.CentralNode(area=area,
                                            location=location,
                                            slot=slot)
          central_node.crate = crate
          self.session.add(central_node)
          crate.central_nodes.append(central_node)
          self.session.commit()

  def add_application_type(self,json_file):
  """
  add_application_type:
   Add an application type to mps_database.  Not done very often.
  inputs:
    json_file: json file defined in main.
  """
    properties = self._load_json_file(json_file)
    if 'app_types' in properties:
      for at in properties['app_types']:
        if self.verbose:
          print("INFO: Adding app type {0}".format(at['name']))
        app_type = models.ApplicationType(name=at['name'],
                                          num_integrators = at['num_integrators'],
                                          analog_channel_count = at['analog_channel_count'],
                                          digital_channel_count = at['digital_channel_count'],
                                          software_channel_count = at['software_channel_count'])
        self.session.add(app_type)
        self.session.commit()

  def check_slots(self,slot,crate):
  """
  check_slots:
   Make sure slot to add is not in use and contained within a crate
   return True if slot is ok and False if it is in use or out of range
  inputs:
    slot: number of slot to add
    crate: mps_database object of a crate to verify new slot
  """
    slot_ok = True
    slots_in_use = [c.slot for c in crate.cards]
    max_slots = crate.num_slots
    if slot > max_slots:
      slot_ok = False
    if slot in slots_in_use:
      slot_ok = False
    return slot_ok

  def add_card(self,json_file):
  """
  add_card_node:
   Add an application card to the mps_database
  inputs:
    json_file: json file defined in main.
  """
    properties = self._load_json_file(json_file)
    if 'cards' in properties:
      for c in properties['cards']:
        types = self.session.query(models.ApplicationType).filter(models.ApplicationType.name==c['type']).all()
        if len(types) > 1:
          print("ERROR: Too many types found for app {0}".format(c['number']))
        if len(types) < 1:
          print("ERROR: No appliation types found for app {0}".format(c['number']))
        if len(types) == 1:
          type = types[0]
          crate = self.find_crate(c,True)
          slot = int(c['slot'])
          if self.check_slots(slot,crate):
            if self.verbose:
              print("INFO: Adding application card {0} in crate {1}-{2}".format(c['number'],crate.location,c['slot']))
            card = models.ApplicationCard(number=c['number'],
                                              slot=c['slot'],
                                              crate=crate,
                                              type=type)
            self.session.add(card)
            crate.cards.append(card)
            type.cards.append(card)
            self.session.commit()
          else:
            print("ERROR: Slot {0} in crate {1} (App {2}) is not available".format(slot,crate.location,c['number']))

  def add_beam_class(self,json_file):
  """
  add_beam_class:
   Add a beam class to the mps_database.
  inputs:
    json_file: json file defined in main.
  """
    added = False
    properties = self._load_json_file(json_file)
    if 'beam_classes' in properties:
      for bc in properties['beam_classes']:
        if self.verbose:
          print("INFO:Adding Beam Class {0}".format(bc['name']))
        beam_class = models.BeamClass(number=bc['number'],
                                      name=bc['name'],
                                      integration_window=bc['integration_window'],
                                      min_period=bc['min_period'],
                                      total_charge=bc['total_charge'])
        self.session.add(beam_class)
        self.session.commit()
        added = True
    return added

  def add_beam_destination(self,json_file):
  """
  add_beam_destination:
   Add a beam destination to the mps_database.
  inputs:
    json_file: json file defined in main.
  """
    added = False
    properties = self._load_json_file(json_file)
    if 'beam_destinations' in properties:
      for bd in properties['beam_destinations']:
        if self.verbose:
          print("INFO: Adding Beam Destination {0}".format(bd['name']))
        beam_destination = models.BeamDestination(name=bd['name'],
                                                  mask=bd['mask'])
        self.session.add(beam_destination)
        self.session.commit()
        added = True
    return added

  def add_mitigation(self):
  """
  add_mitigation:
   Add a mitigation to the mps_database for each combination of beam class and beam destination.
   Called if a new beam class or beam destination is added
  """
    for bc in self.session.query(models.BeamClass).all():
      for bd in self.session.query(models.BeamDestination).all():
        existing_mits = self.session.query(models.Mitigation).filter(models.Mitigation.beam_destination==bd).filter(models.Mitigation.beam_class==bc).all()
        if len(existing_mits) < 1:
          if self.verbose:
            print('INFO: Adding new mitigation for Class {0} and Dest {1}'.format(bc.name,bd.name))
          mitigation = models.Mitigation(beam_destination=bd,beam_class=bc)
          self.session.add(mitigation)
          bc.mitigations.append(mitigation)
          bc.mitigations.append(mitigation)
          self.session.commit()
        else:
          if self.verbose:
            print("INFO: mitigation exists for Class {0} and Dest {1}".format(bc.name,bd.name))

  def add_analog_channel(self,ch):
  """
  add_analog_channel:
   Add an analog_channel to the mps_database.
  inputs:
    ch: datastructure with information about the channel.
  """
    card = self.find_card(ch['appid'])
    integrator = card.type.get_integrator(ch['name'])
    evaluation = 1
    offset = 0
    if offset in ch:
      offset = ch['offset']
    slope = 1
    if slope in ch:
      slope = ch['slope']
    gain_bay = 0
    if gain_bay in ch:
      gain_bay = ch['gain_bay']
    gain_channel = 0
    if gain_channel in ch:
      gain_channel = ch['gain_channel']
    channel = models.AnalogChannel(number=ch['number'],
                                   name=ch['name'],
                                   z_location=ch['z_location'],
                                   auto_reset=ch['auto_reset'],
                                   evaluation=evaluation,
                                   offset=offset,
                                   slope=slope,
                                   integrator=integrator,
                                   gain_bay=gain_bay,
                                   gain_channel=gain_channel,
                                   card=card)
    self.session.add(channel)
    card.channels.append(channel)
    self.session.commit()

  def add_digital_channel(self,ch):
  """
  add_digital_channel:
   Add an analog_channel to the mps_database.
  inputs:
    ch: datastructure with information about the channel.
  """
    card = self.find_card(ch['appid'])
    mon = ''
    evaluation = 0
    alarm_state = 0
    if 'monitored_pv' in ch:
      if ch['monitored_pv'] != '':
        if card.can_have_software():
          mon = ch['monitored_pv']
        else:
          print("ERROR: Trying to put SW channel into app that cannot have SW channels")
          return None
    if card.type.name == 'Wire Scanner':
      evaluation = 1
      alarm_state = 1
    channel = models.DigitalChannel(number=ch['number'],
                                    name=ch['name'],
                                    z_location=ch['z_location'],
                                    auto_reset=ch['auto_reset'],
                                    evaluation=evaluation,
                                    z_name=ch['z_name'],
                                    o_name=ch['o_name'],
                                    alarm_state=alarm_state,
                                    monitored_pv=mon,
                                    card=card)
    self.session.add(channel)
    card.channels.append(channel)
    self.session.commit()

  def add_channel(self,json_file):
  """
  add_channel:
   Decide if new channel is analog or digital and then call appropriate
   child function
  inputs:
    json_file: path to json file from main.
  """
    properties = self._load_json_file(json_file)
    if 'channels' in properties:
      for ch in properties['channels']:
        card = self.find_card(ch['appid'])
        if card.validate_channels(ch['number']):
          if self.verbose:
            print('INFO: Adding Channel {0} in App {1}'.format(ch['name'],ch['appid']))
          if card.can_have_digital():
            self.add_digital_channel(ch)
          elif card.can_have_analog():
            self.add_analog_channel(ch)
          else:
            print('ERROR: Channel is not digital or analog')
        else:
          print("ERROR: Channel {0} in app {1} already used (Type: {2})".format(ch['number'],ch['appid'],card.type.name))

  def add_fault(self,tt):
  """
  add_fault:
   Add a fault to the mps_database.
  inputs:
    tt: datastructure with truth table information.
  """
    existing_fault = self.session.query(models.Fault).filter(models.Fault.name == tt['name']).all()
    if len(existing_fault) > 0:
      print("ERROR: Fault {0} already exists".format(tt['name']))
      return None
    fault = models.Fault(pv=tt['pv'],name=tt['name'])
    return fault

  def get_analog_value(self,state,channel):
  """
  get_analog_value:
   Return proper fault state value for analog fault based on channel integrator
  inputs:
    channel: mps_database object of the channel associated with particular fault
    state: List of items related to this device state.  state[0] is the value if counting
           starting with 0
  """
    integrator = channel.integrator
    return 1 << ((integrator*8)+state[0])

  def find_mitigation(self,dest_name,bc_num):
  """
  find_mitigation:
   Link an mps_database mitigation object with this particular combination of destination and beam class.
  inputs:
    dest_name: string that contains the destination name
    bc_num: integer that contains the beam class number
  return:
    mps_database object mitigation that points to the row of interest.  Will be linked to a fault state
  """
    bc = self.session.query(models.BeamClass).filter(models.BeamClass.number==bc_num).one()
    bd = self.session.query(models.BeamDestination).filter(models.BeamDestination.name==dest_name).one()

    mitigation = self.session.query(models.Mitigation).filter(models.Mitigation.beam_class==bc).filter(models.Mitigation.beam_destination==bd).all()
    if len(mitigation) > 1:
      print("ERROR: Too many mitigations found!")
      return
    if len(mitigation) < 1:
      print("ERROR: Not enough mitigations found")
      return
    return mitigation[0]

  def add_logic(self,json_file):
  """
  add_logic:
   Add a truth table to the mps_database
  inputs:
    json_file: path to json file from main
  """
    properties = self._load_json_file(json_file)
    if "truth_tables" in properties:
      for tt in properties['truth_tables']:
        # First add a new fault.  If fault already exists (based on name), ERROR is thrown.
        fault = self.add_fault(tt)
        if fault is not None:
          bp = 0
          is_analog = False
          # Link each channel to the fault by creating a fault_input with correct bit position (bp)
          for input in tt['inputs']:
            channel = self.session.query(models.Channel).filter(models.Channel.name==input).one()
            fi = models.FaultInput(bit_position=bp,fault=fault,channel=channel)
            channel.fault_input.append(fi)
            self.session.add(fi)
            bp = bp + 1
            if channel.discriminator == 'analog_channel':
              is_analog = True
          # Analog faults can have only one fault_input as they are evaluated "fast
          if is_analog and len(fault.fault_inputs)>1:
            print("ERROR: Too many fault inputs for analog fault! {0}".format(fault.description))
            return
          # If there are ignore conditions, link them
          for ic in tt['ignore_when']:
            ignore_condition = self.session.query(models.IgnoreCondition).filter(models.IgnoreCondition.name==ic).one()
            fault.ignore_conditions.append(ignore_condition)
            ignore_condition.faults.append(fault)
          # Now add the fault_states.  The format of each line in the json file is a list of:
          # tt['states'] is [<value>, <name>, <ShutterBC>,<diag0BC>,<bsyBC>,<hxrBC>,<sxrBC>,<lesaBC>,<lhBC>]
          for s in tt['states']:
            value = s[0]
            name = s[1]
            mask = 4294967295
            if is_analog:
              value = self.get_analog_value(s,channel)
              mask = value
            # for beam class values, the first destination is defined at index 2 in the state information list
            index = 2
            fault_state = models.FaultState(name=name,value=value,mask=mask,fault=fault)
            fault.fault_states.append(fault_state)
            # Find the appropriate mitigation table to link a state to a destination and class
            for dest in self.dests:
              bc = self.conf.get_max_bc()
              if index < 8:
                if s[index] is not None:
                  bc = int(s[index])
              mitigation = self.find_mitigation(dest,bc)
              fault_state.mitigations.append(mitigation)
              mitigation.fault_states.append(fault_state)
              index = index + 1
        if self.verbose:
          print("INFO: Adding logic: {0}".format(fault.name))
        self.session.commit()

  def add_ignore_condition(self,json_file):
  """
  add_ignore_condition:
   Add ignore conditions to the mps_database
  inputs:
    json_file: path to json file from main
  """
    properties = self._load_json_file(json_file)
    if "ignore_conditions" in properties:
      for ic in properties['ignore_conditions']:
        existing_ics = self.session.query(models.IgnoreCondition).filter(models.IgnoreCondition.name==ic['name']).all()
        if len(existing_ics) > 0:
          print("ERROR: Ignore Condition {0} already exists!".format(ic['name']))
          return
        channel = self.session.query(models.Channel).filter(models.Channel.name==ic['channel']).one()
        if self.verbose:
          print("INFO: Adding Ignore Condition: {0}".format(ic['description']))
        ignore_condition = models.IgnoreCondition(name=ic['name'],
                                                  description=ic['description'],
                                                  value=1,
                                                  digital_channel=channel)
        self.session.commit()



parser = argparse.ArgumentParser(description='Add data to MPS Database')
parser.add_argument('-v',action='store_true',default=False,dest='verbose',help='Verbose output')
parser.add_argument('-n',action='store_true',default=False,dest='new_db',help='Create new db')
parser.add_argument('--db',metavar='database',required=True,help='MPS sqlite database file')
parser.add_argument('--file',metavar='jsonFile',required=True,help='relative path to json file of new devices')
args = parser.parse_args()

verbose = False
if args.verbose:
  verbose = True
new_db=False
if args.new_db:
  new_db = True
db_file = args.db
json_file = args.file

new_dest = False
new_bc = False

# The main just calls all the possible additions every time it is run.
# If the json file contains an element of interest for each of the things
# that can be added, they will be added.  If not, that function will return
# and move on to the next one.

add_data = AddDbData(db_file,verbose,new_db)
add_data.add_central_node(json_file)
add_data.add_link_node(json_file)
new_bc = add_data.add_beam_class(json_file)
new_bd = add_data.add_beam_destination(json_file)
if new_bc or new_dest:
  add_data.add_mitigation()
add_data.add_application_type(json_file)
add_data.add_card(json_file)
add_data.add_channel(json_file)
add_data.add_logic(json_file)
add_data.add_ignore_condition(json_file)
