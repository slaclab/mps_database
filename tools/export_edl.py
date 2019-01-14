#!/usr/bin/env python

from Cheetah.Template import Template

from mps_config import MPSConfig, models
from mps_names import MpsName
from sqlalchemy import func

import os
import sys
import argparse

def generateAnalogDevicesEDL(edlFile, templateFile, analogDevices, mpsName):
  data=templateFile.read()

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
  for analogDevice in analogDevices:
    name = mpsName.getAnalogDeviceName(analogDevice)

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

#    for state in analogDevice.device_type.states:
          crates.append(analogDevice.channel.card.crate.get_name())#number)
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
            ign_pv_name = '-'

          ign.append(ign_pv_name)

#          if (len(ignore_condition) > 0):
#            print '{2}: {0}, {1}'.format(ignore_condition[0].analog_device_id, 
#                                         ignore_condition[0].fault_state_id,
#                                         ign_pv_name)
#          else:
#            print '{0}: -, -'.format(ign_pv_name)

    
#  print "Found " + str(bitCounter) + " bits."

  nameSpace={'ANALOG_DEVICES': str(bitCounter),#str(len(analogDevices)),
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

  t = Template(data, searchList=[nameSpace])
  edlFile.write("%s" % t)
#  templateFile.close()
  edlFile.close()

def generateDeviceInputsEDL(edlFile, templateFile, deviceInputs, mpsName):
  data=templateFile.read()

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

  for deviceInput in deviceInputs:
    name = mpsName.getDeviceInputName(deviceInput)

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
    
  nameSpace={'DEVICE_INPUTS': str(len(deviceInputs)),
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

  t = Template(data, searchList=[nameSpace])
  edlFile.write("%s" % t)
#  templateFile.close()
  edlFile.close()

def generateFaultsEDL(edlFile, templateFile, faults, mpsName):
  data=templateFile.read()

  desc=[]
  fault_pv=[]
  latched=[]
  ignore=[]
  unlatch=[]

  for fault in faults:
    name = mpsName.getFaultName(fault)

    desc.append(fault.description)
    fault_pv.append(name)
    latched.append(name + "_MPS")
    ignore.append(name + "_IGN")
    unlatch.append(name + "_UNLH")
    
  nameSpace={'FAULTS': str(len(faults)),
             'DESC': desc,
             'FLT_PV': fault_pv,
             'FLT_PV_LATCHED': latched,
             'FLT_PV_IGNORE': ignore,
             'FLT_PV_UNLATCH': unlatch,
             }

  t = Template(data, searchList=[nameSpace])
  edlFile.write("%s" % t)
#  templateFile.close()
  edlFile.close()

def generateAnalogBypassEDL(edlFile, templateFile, analogDevices, mpsName):
  data=templateFile.read()

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
  for analogDevice in analogDevices:
    name = mpsName.getAnalogDeviceName(analogDevice)

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

  nameSpace={'ANALOG_DEVICES': str(bitCounter),#str(len(analogDevices)),
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

  t = Template(data, searchList=[nameSpace])
  edlFile.write("%s" % t)
#  templateFile.close()
  edlFile.close()

def generateBypassEDL(edlFile, templateFile, deviceInputs, mpsName):
  data=templateFile.read()

  byps=[]
  bypv=[]
  bypd=[]
  bypt=[]
  names=[]
  pvs=[]
  expd=[]
  rtim=[]

  for deviceInput in deviceInputs:
    name = mpsName.getDeviceInputName(deviceInput)

#    cards.append(deviceInput.channel.card.number)
    byps.append('{0}_BYPS'.format(name))
    bypv.append('{0}_BYPV'.format(name))
    bypd.append('{0}_BYPD'.format(name))
    bypt.append('{0}_BYPT'.format(name))
    names.append(name)
    pvs.append('{0}_MPSC'.format(name))
    expd.append('{0}_BYP_END'.format(name))
    rtim.append('{0}_BYPT'.format(name))
    
  nameSpace={'DEVICE_INPUTS': str(len(deviceInputs)),
             'DI_BYPS': byps,
             'DI_BYPV': bypv,
             'DI_BYPD': bypd,
             'DI_BYPT': bypt,
             'DI_NAME': names,
             'DI_PV': pvs,
             'DI_EXPD': expd,
             'DI_RTIM': rtim,
             }

  t = Template(data, searchList=[nameSpace])
  edlFile.write("%s" % t)
#  templateFile.close()
  edlFile.close()

def createLinkNodeDirectories(linkNodeDir, linkNodes, mpsName):
  if not os.path.isdir(linkNodeDir):
    print 'INFO: {0} directory for link node files does not exist, trying to create it'.format(linkNodeDir)
    try:
      os.mkdir(linkNodeDir)
    except:
      print 'ERROR: Failed to create {0} directory'.format(linkNodeDir)
      exit(-1)

  for ln in linkNodes:
    ln_dir = linkNodeDir + '/' + ln.get_name()
    if not os.path.isdir(ln_dir):
      os.mkdir(ln_dir)

#=== MAIN ==================================================================================

parser = argparse.ArgumentParser(description='Export EPICS template database')
parser.add_argument('database', metavar='db', type=file, nargs=1, 
                    help='database file name (e.g. mps_gun.db)')

parser.add_argument('--device-inputs-edl', metavar='file', type=argparse.FileType('w'), nargs='?',
                    help='epics template file name for digital channels (e.g. device_inputs.edl)')
parser.add_argument('--device-inputs-template', metavar='file', type=argparse.FileType('r'), nargs='?',
                    help='Cheetah template file name for digital channels (e.g. device_inputs.tmpl)')

parser.add_argument('--analog-devices-edl', metavar='file', type=argparse.FileType('w'), nargs='?',
                    help='epics template file name for analog channels (e.g. analog_devices.edl)')
parser.add_argument('--analog-devices-template', metavar='file', type=argparse.FileType('r'), nargs='?',
                    help='Cheetah template file name for analog channels (e.g. analog_devices.tmpl)')

parser.add_argument('--faults-edl', metavar='file', type=argparse.FileType('w'), nargs='?',
                    help='epics template file name for faults (e.g. faults.edl)')
parser.add_argument('--faults-template', metavar='file', type=argparse.FileType('r'), nargs='?',
                    help='Cheetah template file name for faults (e.g. faults.tmpl)')

parser.add_argument('--bypass-digital-edl', metavar='file', type=argparse.FileType('w'), nargs='?',
                    help='epics template file name for bypass info panel (e.g. bypass-digital.edl)')
parser.add_argument('--bypass-analog-edl', metavar='file', type=argparse.FileType('w'), nargs='?',
                    help='epics template file name for bypass info panel (e.g. bypass-analog.edl)')
parser.add_argument('--bypass-digital-template', metavar='file', type=argparse.FileType('r'), nargs='?',
                    help='Cheetah template file name for bypass (e.g. bypass.tmpl)')
parser.add_argument('--bypass-analog-template', metavar='file', type=argparse.FileType('r'), nargs='?',
                    help='Cheetah template file name for bypass (e.g. bypass.tmpl)')
parser.add_argument('--link-nodes', metavar='link_node_dir', type=str, nargs='?',
                    help='Generate link node screens under the specified directory' \
                      'need --device-inputs, --analog-devices, --faults and --bypass options!')

args = parser.parse_args()

mps = MPSConfig(args.database[0].name)
session = mps.session
mpsName = MpsName(session)

linkNodes = None
if (args.link_nodes):
  linkNodes = session.query(models.LinkNode).all()
  createLinkNodeDirectories(args.link_nodes, linkNodes, mpsName)

if (args.device_inputs_edl and args.device_inputs_template):
  if linkNodes == None:
    generateDeviceInputsEDL(args.device_inputs_edl, args.device_inputs_template,
                            session.query(models.DeviceInput).all(), mpsName, None)
  else:
    # Generate one edl file per link node
    fileName = args.device_inputs_edl.name.split('/')[len(args.device_inputs_edl.name.split('/'))-1]
    for ln in linkNodes:
      dirName = args.link_nodes + '/' + ln.get_name() + '/'

      deviceInputs = []
      for c in ln.crate.cards:
        if len(c.digital_channels) > 0:
          for dc in c.digital_channels:
            deviceInputs.append(dc.device_input)

      if len(deviceInputs) > 0:
        f = open(dirName + fileName, 'w')
        generateDeviceInputsEDL(f, args.device_inputs_template,
                                deviceInputs, mpsName)
        
        args.device_inputs_template.seek(0)

if (args.analog_devices_edl and args.analog_devices_template):
  if linkNodes == None:
    generateAnalogDevicesEDL(args.analog_devices_edl, args.analog_devices_template,
                             session.query(models.AnalogDevice).all(), mpsName)
  else:
    # Generate one edl file per link node
    fileName = args.analog_devices_edl.name.split('/')[len(args.analog_devices_edl.name.split('/'))-1]
    for ln in linkNodes:
      dirName = args.link_nodes + '/' + ln.get_name() + '/'

      analogDevices = []
      for c in ln.crate.cards:
        if len(c.analog_channels) > 0:
          for ac in c.analog_channels:
            ad = session.query(models.AnalogDevice).filter(models.AnalogDevice.channel_id==ac.id).one()
            analogDevices.append(ad)

      if len(analogDevices) > 0:
        f = open(dirName + fileName, 'w')
        generateAnalogDevicesEDL(f, args.analog_devices_template,
                                 analogDevices, mpsName)
        
        args.analog_devices_template.seek(0)

if (args.faults_edl and args.faults_template):
  if linkNodes == None:
    generateFaultsEDL(args.faults_edl, args.faults_template,
                      session.query(models.Fault).all(), mpsName)
  else:
    # Generate one edl file per link node
    fileName = args.faults_edl.name.split('/')[len(args.faults_edl.name.split('/'))-1]
    for ln in linkNodes:
      dirName = args.link_nodes + '/' + ln.get_name() + '/'

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
        f = open(dirName + fileName, 'w')
        generateFaultsEDL(f, args.faults_template,
                          faults, mpsName)
        
        args.faults_template.seek(0)
    

if (args.bypass_digital_edl and args.bypass_digital_template):
  if linkNodes == None:
    generateBypassEDL(args.bypass_digital_edl, args.bypass_digital_template,
                      session.query(models.DeviceInput).all(), mpsName)
  else:
    # Generate one edl file per link node
    fileName = args.bypass_digital_edl.name.split('/')[len(args.bypass_digital_edl.name.split('/'))-1]
    for ln in linkNodes:
      dirName = args.link_nodes + '/' + ln.get_name() + '/'

      deviceInputs = []
      for c in ln.crate.cards:
        if len(c.digital_channels) > 0:
          for dc in c.digital_channels:
            deviceInputs.append(dc.device_input)

      if len(deviceInputs) > 0:
        f = open(dirName + fileName, 'w')
        generateBypassEDL(f, args.bypass_digital_template,
                          deviceInputs, mpsName)
        
        args.bypass_digital_template.seek(0)

if (args.bypass_analog_edl and args.bypass_analog_template):
  if linkNodes == None:
    generateAnalogBypassEDL(args.bypass_analog_edl, args.bypass_analog_template,
                            session.query(models.AnalogDevice).all(), mpsName)
  else:
    # Generate one edl file per link node
    fileName = args.bypass_analog_edl.name.split('/')[len(args.bypass_analog_edl.name.split('/'))-1]
    for ln in linkNodes:
      dirName = args.link_nodes + '/' + ln.get_name() + '/'

      analogDevices = []
      for c in ln.crate.cards:
        if len(c.analog_channels) > 0:
          for ac in c.analog_channels:
            ad = session.query(models.AnalogDevice).filter(models.AnalogDevice.channel_id==ac.id).one()
            analogDevices.append(ad)

      if len(analogDevices) > 0:
        f = open(dirName + fileName, 'w')
        generateAnalogBypassEDL(f, args.bypass_analog_template,
                                analogDevices, mpsName)
        
        args.bypass_analog_template.seek(0)


session.close()

