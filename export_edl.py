#!/usr/bin/env python

from Cheetah.Template import Template

from mps_config import MPSConfig, models
from sqlalchemy import func
import sys
import argparse

def generateAnalogDevicesEDL(edlFile, templateFile, analogDevices):
  data=templateFile.read()

  crates=[]
  cards=[]
  channels=[]
  byps=[]
  bypv=[]
  names=[]
  pvs=[]
  devpv=[]
  latched=[]
  unlatch=[]
  bits=[]

  bitCounter = 0
  for analogDevice in analogDevices:
    for state in analogDevice.device_type.states:
      crates.append(analogDevice.channel.card.crate.number)
      cards.append(analogDevice.channel.card.number)
      channels.append(analogDevice.channel.number)
      byps.append('MPS:ANALOG:{0}_BYPS'.format(analogDevice.channel.name))
      bypv.append('MPS:ANALOG:{0}_BYPV'.format(analogDevice.channel.name))
      names.append('{0} {1}'.format(analogDevice.channel.name, state.name))
      pvs.append('MPS:ANALOG:{0}_{1}'.format(analogDevice.channel.name, state.name))
      devpv.append('MPS:ANALOG:{0}'.format(analogDevice.channel.name))
      latched.append('MPS:ANALOG:{0}_LATCHED'.format(analogDevice.channel.name))
      unlatch.append('MPS:ANALOG:{0}_UNLATCH'.format(analogDevice.channel.name))
      bits.append("0x%0.4X" % state.mask)
      bitCounter = bitCounter + 1
    
  print "Found " + str(bitCounter) + " bits."

  nameSpace={'ANALOG_DEVICES': str(bitCounter),#str(len(analogDevices)),
             'AD_CRATE': crates,
             'AD_CARD': cards,
             'AD_CHANNEL': channels,
             'AD_BIT': bits,
             'AD_BYPS': byps,
             'AD_BYPV': bypv,
             'AD_NAME': names,
             'AD_PV': pvs,
             'AD_DEVPV': devpv, # PV of the whole device, not each threshold
             'AD_PV_LATCHED': latched,
             'AD_PV_UNLATCH': unlatch,
             }

  t = Template(data, searchList=[nameSpace])
  edlFile.write("%s" % t)
  templateFile.close()
  edlFile.close()

def generateDeviceInputsEDL(edlFile, templateFile, deviceInputs):
  data=templateFile.read()

  crates=[]
  cards=[]
  channels=[]
  byps=[]
  bypv=[]
  names=[]
  pvs=[]
  latched=[]
  unlatch=[]

  for deviceInput in deviceInputs:
    crates.append(deviceInput.channel.card.crate.number)
    cards.append(deviceInput.channel.card.number)
    channels.append(deviceInput.channel.number)
    byps.append('MPS:DIGITAL:{0}_BYPS'.format(deviceInput.channel.name))
    bypv.append('MPS:DIGITAL:{0}_BYPV'.format(deviceInput.channel.name))
    names.append(deviceInput.channel.name)
    pvs.append('MPS:DIGITAL:{0}'.format(deviceInput.channel.name))
    latched.append('MPS:DIGITAL:{0}_MPS'.format(deviceInput.channel.name))
    unlatch.append('MPS:DIGITAL:{0}_UNLH'.format(deviceInput.channel.name))
    
  nameSpace={'DEVICE_INPUTS': str(len(deviceInputs)),
             'DI_CRATE': crates,
             'DI_CARD': cards,
             'DI_CHANNEL': channels,
             'DI_BYPS': byps,
             'DI_BYPV': bypv,
             'DI_NAME': names,
             'DI_PV': pvs,
             'DI_PV_LATCHED': latched,
             'DI_PV_UNLATCH': unlatch,
             }

  t = Template(data, searchList=[nameSpace])
  edlFile.write("%s" % t)
  templateFile.close()
  edlFile.close()

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

args = parser.parse_args()

mps = MPSConfig(args.database[0].name)
session = mps.session

if (args.device_inputs_edl and args.device_inputs_template):
  generateDeviceInputsEDL(args.device_inputs_edl, args.device_inputs_template,
                          session.query(models.DeviceInput).all())

if (args.analog_devices_edl and args.analog_devices_template):
  generateAnalogDevicesEDL(args.analog_devices_edl, args.analog_devices_template,
                           session.query(models.AnalogDevice).all())

session.close()

