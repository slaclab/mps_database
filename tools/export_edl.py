#!/usr/bin/env python

from Cheetah.Template import Template

from mps_config import MPSConfig, models
from mps_names import MpsName
from sqlalchemy import func
from mps_app_reader import MpsAppReader

import os
import sys
import argparse

def generate_analog_devices_EDL(edl_file, template_file, analog_devices, mps_name):
  data=template_file.read()

  crates=[]
  cards=[]
  channels=[]
  byps=[]
  bypd=[]
  bypt=[]
  expd=[]
  names=[]
  pvs=[]
  devpv=[]
  latched=[]
  unlatch=[]
  bits=[]
  ign=[]

  bitCounter = 0
  for analogDevice in analog_devices:
    name = mps_name.getAnalogDeviceName(analogDevice)

    faultInputs = session.query(models.FaultInput).filter(models.FaultInput.device_id==analogDevice.id).all()
    for fi in faultInputs:
      faults = session.query(models.Fault).filter(models.Fault.id==fi.fault_id).all()
      for fa in faults:
        faultStates = session.query(models.FaultState).filter(models.FaultState.fault_id==fa.id).all()
        for state in faultStates:
          #print name + " " + state.device_state.name

          # Add a IGNORED PV only if device appears in an ignoreCondition
          ignore_condition = session.query(models.IgnoreCondition).\
              filter(models.IgnoreCondition.analog_device_id==analogDevice.id).all()

          crates.append(analogDevice.channel.card.crate.get_name())
          slot=str(analogDevice.channel.card.slot_number)
          if (analogDevice.channel.card.amc == 0):
            slot=slot+':AMC0'
          elif (analogDevice.channel.card.amc == 1):
            slot=slot+':AMC1'
          else:
            slot=slot+':?'
          cards.append(slot)
          channels.append(analogDevice.channel.number)
          byps.append('{0}:{1}_BYPS'.format(name, fa.name))
          bypd.append('{0}:{1}_BYPD'.format(name, fa.name))
          bypt.append('{0}:{1}_BYPT'.format(name, fa.name))
          expd.append('{0}:{1}_BYP_END'.format(name, fa.name))
          names.append('{0}:{1}'.format(name, state.device_state.name))
          pvs.append('{0}:{1}_MPSC'.format(name, state.device_state.name))
          devpv.append('{0}'.format(name))
          latched.append('{0}:{1}_MPS'.format(name, state.device_state.name))
          unlatch.append('{0}:{1}_UNLH'.format(name, state.device_state.name))
          bits.append("0x%0.4X" % 0)#state.mask)
          bitCounter = bitCounter + 1

          ign_pv_name = '{0}:{1}_IGN'.format(name, fa.name)
          if (len(ignore_condition) > 0):
            if (ignore_condition[0].fault_state_id == None):
              ign_pv_name = '{0}:MPSC_IGN'.format(name)
            elif (ignore_condition[0].analog_device_id == None):
              ign_pv_name = '-'
            else:
              if (ignore_condition[0].fault_state.device_state_id != state.device_state.id):
                ign_pv_name = '-'
          else:
            ign_pv_name = '-'

          ign.append(ign_pv_name)

#          if (len(ignore_condition) > 0):
#            print '{2}: {0}, {1}'.format(ignore_condition[0].analog_device_id, 
#                                         ignore_condition[0].fault_state_id,
#                                         ign_pv_name)
#          else:
#            print '{0}: -, -'.format(ign_pv_name)

    
#  print "Found " + str(bitCounter) + " bits."

  macros={'ANALOG_DEVICES': str(bitCounter),#str(len(analog_devices)),
             'AD_CRATE': crates,
             'AD_CARD': cards,
             'AD_CHANNEL': channels,
             'AD_BIT': bits,
             'AD_BYPS': byps,
             'AD_BYPD': bypd,
             'AD_BYPT': bypt,
             'AD_IGN': ign,
             'AD_EXPD': expd,
             'AD_NAME': names,
             'AD_PV': pvs,
             'AD_DEVPV': pvs, #devpv, # PV of the whole device, not each threshold
             'AD_PV_LATCHED': latched,
             'AD_PV_UNLATCH': unlatch,
             }

  t = Template(data, searchList=[macros])
  edl_file.write("%s" % t)
#  template_file.close()
  edl_file.close()

def generate_device_inputs_EDL(edl_file, template_file, device_inputs, mps_name):
  data=template_file.read()

  crates=[]
  cards=[]
  channels=[]
  byps=[]
  bypv=[]
  bypd=[]
  bypt=[]
  expd=[]
  names=[]
  pvs=[]
  latched=[]
  unlatch=[]

  for deviceInput in device_inputs:
    name = mps_name.getDeviceInputName(deviceInput)

    crates.append(deviceInput.channel.card.crate.get_name())#number)
    slot=str(deviceInput.channel.card.slot_number)
    if (deviceInput.channel.card.amc == 0):
      slot=slot+':AMC0'
    elif (deviceInput.channel.card.amc == 1):
      slot=slot+':AMC1'
    else:
      slot=slot+':RTM'
    cards.append(slot)

#    cards.append(deviceInput.channel.card.number)
    channels.append(deviceInput.channel.number)
    byps.append('{0}_BYPS'.format(name))
    bypv.append('{0}_BYPV'.format(name))
    bypd.append('{0}_BYPD'.format(name))
    bypt.append('{0}_BYPT'.format(name))
    expd.append('{0}_BYP_END'.format(name))
    names.append(name)
    pvs.append('{0}_MPSC'.format(name))
    latched.append('{0}_MPS'.format(name))
    unlatch.append('{0}_UNLH'.format(name))
    
  macros={'DEVICE_INPUTS': str(len(device_inputs)),
             'DI_TEST': '1',
             'DI_CRATE': crates,
             'DI_CARD': cards,
             'DI_CHANNEL': channels,
             'DI_BYPS': byps,
             'DI_BYPV': bypv,
             'DI_BYPD': bypd,
             'DI_BYPT': bypt,
             'DI_EXPD': expd,
             'DI_NAME': names,
             'DI_PV': pvs,
             'DI_PV_LATCHED': latched,
             'DI_PV_UNLATCH': unlatch,
             }

  t = Template(data, searchList=[macros])
  edl_file.write("%s" % t)
#  template_file.close()
  edl_file.close()

def generateFaultsEDL(edl_file, template_file, faults, mps_name):
  data=template_file.read()

  desc=[]
  fault_pv=[]
  latched=[]
  ignore=[]
  unlatch=[]

  for fault in faults:
    name = mps_name.getFaultName(fault)

    desc.append(fault.description)
    fault_pv.append(name)
    latched.append(name + "_MPS")
    ignore.append(name + "_IGN")
    unlatch.append(name + "_UNLH")
    
  macros={'FAULTS': str(len(faults)),
             'DESC': desc,
             'FLT_PV': fault_pv,
             'FLT_PV_LATCHED': latched,
             'FLT_PV_IGNORE': ignore,
             'FLT_PV_UNLATCH': unlatch,
             }

  t = Template(data, searchList=[macros])
  edl_file.write("%s" % t)
#  template_file.close()
  edl_file.close()

def generate_analog_bypass_EDL(edl_file, template_file, analog_devices, mps_name):
  data=template_file.read()

  byps=[]
  bypd=[]
  bypt=[]
  expd=[]
  names=[]
  pvs=[]
  devpv=[]
  expd=[]
  rtim=[]

  bitCounter = 0
  for analogDevice in analog_devices:
    name = mps_name.getAnalogDeviceName(analogDevice)

    faultInputs = session.query(models.FaultInput).filter(models.FaultInput.device_id==analogDevice.id).all()
    for fi in faultInputs:
      faults = session.query(models.Fault).filter(models.Fault.id==fi.fault_id).all()
      for fa in faults:
        faultStates = session.query(models.FaultState).filter(models.FaultState.fault_id==fa.id).all()
        for state in faultStates:
#          print name + " " + state.device_state.name
#    for state in analogDevice.device_type.states:
          slot=str(analogDevice.channel.card.slot_number)
          if (analogDevice.channel.card.amc == 0):
            slot=slot+':AMC0'
          elif (analogDevice.channel.card.amc == 1):
            slot=slot+':AMC1'
          else:
            slot=slot+':?'
          byps.append('{0}:{1}_BYPS'.format(name, fa.name))
          bypd.append('{0}:{1}_BYPD'.format(name, fa.name))
          bypt.append('{0}:{1}_BYPT'.format(name, fa.name))
          names.append('{0}:{1}'.format(name, state.device_state.name))
          pvs.append('{0}:{1}_MPSC'.format(name, state.device_state.name))
          devpv.append('{0}'.format(name))
          bitCounter = bitCounter + 1
          expd.append('{0}:{1}_BYP_END'.format(name, fa.name))
          rtim.append('{0}:{1}_BYPT'.format(name, fa.name))

  macros={'ANALOG_DEVICES': str(bitCounter),#str(len(analog_devices)),
             'DEVICE_INPUTS': '0',
             'DI_BYPS': byps,
             'DI_BYPD': bypd,
             'DI_BYPT': bypt,
             'DI_NAME': names,
             'DI_PV': pvs,
             'DI_DEVPV': pvs, #devpv, # PV of the whole device, not each threshold
             'DI_EXPD': expd,
             'DI_RTIM': rtim,
             }

  t = Template(data, searchList=[macros])
  edl_file.write("%s" % t)
#  template_file.close()
  edl_file.close()

def generate_bypass_EDL(edl_file, template_file, device_inputs, mps_name):
  data=template_file.read()

  byps=[]
  bypv=[]
  bypd=[]
  bypt=[]
  names=[]
  pvs=[]
  expd=[]
  rtim=[]

  for deviceInput in device_inputs:
    name = mps_name.getDeviceInputName(deviceInput)

#    cards.append(deviceInput.channel.card.number)
    byps.append('{0}_BYPS'.format(name))
    bypv.append('{0}_BYPV'.format(name))
    bypd.append('{0}_BYPD'.format(name))
    bypt.append('{0}_BYPT'.format(name))
    names.append(name)
    pvs.append('{0}_MPSC'.format(name))
    expd.append('{0}_BYP_END'.format(name))
    rtim.append('{0}_BYPT'.format(name))
    
  macros={'DEVICE_INPUTS': str(len(device_inputs)),
             'DI_BYPS': byps,
             'DI_BYPV': bypv,
             'DI_BYPD': bypd,
             'DI_BYPT': bypt,
             'DI_NAME': names,
             'DI_PV': pvs,
             'DI_EXPD': expd,
             'DI_RTIM': rtim,
             }

  t = Template(data, searchList=[macros])
  edl_file.write("%s" % t)
  edl_file.close()

def generate_link_node_EDL(edl_file, template_file, session, link_node, mps_name, mps_app_reader, verbose):
#  mps_app_reader.print_app_data()
  data=template_file.read()

  if verbose:
    print("Generating screens for {} ({})".format(link_node.get_name(), link_node.get_type()))
#    print("{} information: {}".format(link_node.get_name(), mps_app_reader.link_nodes[link_node.get_name()]))

  try:
    app_cards = session.query(models.ApplicationCard).\
        filter(models.ApplicationCard.link_node_id==link_node.id).all()
  except Exception as e:
    print e
    print('ERROR')
    return

  macros={
    'link_node':link_node,
    'app_reader':mps_app_reader,
    'template_dir':os.path.dirname(template_file.name)
    }
 
  # The logic to setup the edl panel is in the template cheetah file
  t = Template(data, searchList=[macros])
  edl_file.write("%s" % t)
  edl_file.close()

def create_link_node_directories(link_node_dir, link_nodes, mps_name):
  if not os.path.isdir(link_node_dir):
    print 'INFO: {0} directory for link node files does not exist, trying to create it'.format(link_node_dir)
    try:
      os.mkdir(link_node_dir)
    except:
      print 'ERROR: Failed to create {0} directory'.format(link_node_dir)
      exit(-1)

  for ln in link_nodes:
    ln_dir = link_node_dir + '/' + ln.get_name()
    if not os.path.isdir(ln_dir):
      os.mkdir(ln_dir)

#=== MAIN ==================================================================================

parser = argparse.ArgumentParser(description='Export EPICS template database')
parser.add_argument('database', metavar='db', type=file, nargs=1, 
                    help='database file name (e.g. mps_gun.db)')

parser.add_argument('--device-inputs-template', metavar='file', type=argparse.FileType('r'), nargs='?',
                    help='Cheetah template file name for digital channels (e.g. device_inputs.tmpl)')

parser.add_argument('--analog-devices-template', metavar='file', type=argparse.FileType('r'), nargs='?',
                    help='Cheetah template file name for analog channels (e.g. analog_devices.tmpl)')

parser.add_argument('--faults-template', metavar='file', type=argparse.FileType('r'), nargs='?',
                    help='Cheetah template file name for faults (e.g. faults.tmpl)')

parser.add_argument('--bypass-digital-template', metavar='file', type=argparse.FileType('r'), nargs='?',
                    help='Cheetah template file name for bypass (e.g. bypass.tmpl)')

parser.add_argument('--bypass-analog-template', metavar='file', type=argparse.FileType('r'), nargs='?',
                    help='Cheetah template file name for bypass (e.g. bypass.tmpl)')

parser.add_argument('--link-node-template', metavar='file', type=argparse.FileType('r'), nargs='?',
                    help='Cheetah template file name for link node screen (e.g. link_node.tmpl)')

parser.add_argument('--link-nodes', metavar='link_node_dir', type=str, nargs='?',
                    help='Generate link node screens under the specified directory' \
                      'need --device-inputs, --analog-devices, --faults and --bypass options!')

parser.add_argument('--link-node', metavar='link_node_name', type=str, nargs='?',
                    help='If provided generate screens only for the specified link node'\
                      'need --link-nodes and related options specified')

parser.add_argument('-v', action='store_true', default=False,
                    dest='verbose', help='Verbose output')

args = parser.parse_args()
verbose = args.verbose

mps_app_reader = MpsAppReader(db_file=args.database[0].name, verbose=args.verbose)

mps = MPSConfig(args.database[0].name)
session = mps.session
mps_name = MpsName(session)

link_nodes = None
link_node = None
if (args.link_nodes):
  link_nodes = session.query(models.LinkNode).all()
  create_link_node_directories(args.link_nodes, link_nodes, mps_name)
  if (args.link_node):
    link_node = args.link_node
    if (len(filter (lambda x : x.get_name() == link_node, link_nodes)) != 1):
      print 'ERROR: Can\'t find sioc named {0}'.format(link_node)
      exit(0)
    else:
      link_nodes = filter (lambda x : x.get_name() == link_node, link_nodes)
      print 'INFO: Producing screens for SIOC {0} only'.format(link_node)

if (args.device_inputs_template):
  # Generate one edl file per link node
  file_name = 'device_inputs.edl'
  for ln in link_nodes:
    dir_name = args.link_nodes + '/' + ln.get_name() + '/'

    device_inputs = []
    for c in ln.crate.cards:
      if len(c.digital_channels) > 0:
        for dc in c.digital_channels:
          device_inputs.append(dc.device_input)

    if len(device_inputs) > 0:
      f = open(dir_name + file_name, 'w')
      generate_device_inputs_EDL(f, args.device_inputs_template,
                                 device_inputs, mps_name)

      args.device_inputs_template.seek(0)

if (args.analog_devices_template):
  # Generate one edl file per link node
  file_name = 'analog_devices.edl'
  for ln in link_nodes:
    dir_name = args.link_nodes + '/' + ln.get_name() + '/'

    analog_devices = []
    for c in ln.crate.cards:
      if len(c.analog_channels) > 0:
        for ac in c.analog_channels:
          ad = session.query(models.AnalogDevice).filter(models.AnalogDevice.channel_id==ac.id).one()
          analog_devices.append(ad)

    if len(analog_devices) > 0:
      f = open(dir_name + file_name, 'w')
      generate_analog_devices_EDL(f, args.analog_devices_template,
                                  analog_devices, mps_name)

      args.analog_devices_template.seek(0)

if (args.faults_template):
  # Generate one edl file per link node
  file_name = 'faults.edl'
  for ln in link_nodes:
    dir_name = args.link_nodes + '/' + ln.get_name() + '/'

    faults = []
    for c in ln.crate.cards:
      if len(c.digital_channels) > 0:
        # Digital Faults
        for digitalChannel in c.digital_channels:
          device = session.query(models.DigitalDevice).\
              filter(models.DigitalDevice.id==digitalChannel.device_input.digital_device_id).one()
          fault_inputs = session.query(models.FaultInput).\
              filter(models.FaultInput.device_id==device.id)
          for fi in fault_inputs:
            flt = session.query(models.Fault).filter(models.Fault.id ==fi.fault_id).one()
            faults.append(flt)

        # Analog Faults
      if len(c.analog_channels) > 0:
        for analogChannel in c.analog_channels:
          device = session.query(models.AnalogDevice).filter(models.AnalogDevice.channel_id==analogChannel.id).one()
          fault_inputs = session.query(models.FaultInput).\
              filter(models.FaultInput.device_id==device.id)
          for fi in fault_inputs:
            flt = session.query(models.Fault).filter(models.Fault.id ==fi.fault_id).one()
            faults.append(flt)

    if len(faults) > 0:
      f = open(dir_name + file_name, 'w')
      generateFaultsEDL(f, args.faults_template,
                        faults, mps_name)

      args.faults_template.seek(0)
    

if (args.bypass_digital_template):
  # Generate one edl file per link node
  file_name = 'bypass_digital.edl'
  for ln in link_nodes:
    dir_name = args.link_nodes + '/' + ln.get_name() + '/'

    device_inputs = []
    for c in ln.crate.cards:
      if len(c.digital_channels) > 0:
        for dc in c.digital_channels:
          device_inputs.append(dc.device_input)

    if len(device_inputs) > 0:
      f = open(dir_name + file_name, 'w')
      generate_bypass_EDL(f, args.bypass_digital_template,
                          device_inputs, mps_name)

      args.bypass_digital_template.seek(0)

if (args.bypass_analog_template):
  # Generate one edl file per link node
  file_name = 'bypass_analog.edl'
  for ln in link_nodes:
    dir_name = args.link_nodes + '/' + ln.get_name() + '/'

    analog_devices = []
    for c in ln.crate.cards:
      if len(c.analog_channels) > 0:
        for ac in c.analog_channels:
          ad = session.query(models.AnalogDevice).filter(models.AnalogDevice.channel_id==ac.id).one()
          analog_devices.append(ad)

    if len(analog_devices) > 0:
      f = open(dir_name + file_name, 'w')
      generate_analog_bypass_EDL(f, args.bypass_analog_template,
                                 analog_devices, mps_name)

      args.bypass_analog_template.seek(0)

if (args.link_node_template):
  file_name = 'link_node.edl'
  for ln in link_nodes:
    dir_name = args.link_nodes + '/' + ln.get_name() + '/'
    f = open(dir_name + file_name, 'w')
    generate_link_node_EDL(f, args.link_node_template, session, ln, mps_name, mps_app_reader, verbose)
    args.link_node_template.seek(0)
#    mps_app_reader.pretty_print()

session.close()

