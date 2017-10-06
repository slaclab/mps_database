#!/usr/bin/env python

from Cheetah.Template import Template

from mps_config import MPSConfig, models
from mps_names import MpsName
from sqlalchemy import func
import sys
import argparse

def generateAnalogDevicesEDL(edlFile, templateFile, analogDevices, mpsName):
  data=templateFile.read()

  crates=[]
  cards=[]
  channels=[]
  byps=[]
  bypv=[]
  bypd=[]
  names=[]
  pvs=[]
  devpv=[]
  latched=[]
  unlatch=[]
  bits=[]

  bitCounter = 0
  for analogDevice in analogDevices:
    name = mpsName.getAnalogDeviceName(analogDevice)

    faultInputs = session.query(models.FaultInput).filter(models.FaultInput.device_id==analogDevice.id).all()
    for fi in faultInputs:
      faults = session.query(models.Fault).filter(models.Fault.id==fi.fault_id).all()
      for fa in faults:
        faultStates = session.query(models.FaultState).filter(models.FaultState.fault_id==fa.id).all()
        for state in faultStates:
          print name + " " + state.device_state.name
#    for state in analogDevice.device_type.states:
          crates.append(analogDevice.channel.card.crate.number)
          cards.append(analogDevice.channel.card.number)
          channels.append(analogDevice.channel.number)
          byps.append('{0}:{1}_BYPS'.format(name, fa.name))
          bypv.append('{0}:{1}_BYPV'.format(name, fa.name))
          bypd.append('{0}:{1}_BYPD'.format(name, fa.name))
          names.append('{0}:{1}'.format(name, state.device_state.name))
          pvs.append('{0}:{1}_MPSC'.format(name, state.device_state.name))
          devpv.append('{0}'.format(name))
          latched.append('{0}:{1}_MPS'.format(name, state.device_state.name))
          unlatch.append('{0}:{1}_UNLH'.format(name, state.device_state.name))
          bits.append("0x%0.4X" % 0)#state.mask)
          bitCounter = bitCounter + 1
    
  print "Found " + str(bitCounter) + " bits."

  nameSpace={'ANALOG_DEVICES': str(bitCounter),#str(len(analogDevices)),
             'AD_CRATE': crates,
             'AD_CARD': cards,
             'AD_CHANNEL': channels,
             'AD_BIT': bits,
             'AD_BYPS': byps,
             'AD_BYPV': bypv,
             'AD_BYPD': bypd,
             'AD_NAME': names,
             'AD_PV': pvs,
             'AD_DEVPV': pvs, #devpv, # PV of the whole device, not each threshold
             'AD_PV_LATCHED': latched,
             'AD_PV_UNLATCH': unlatch,
             }

  t = Template(data, searchList=[nameSpace])
  edlFile.write("%s" % t)
  templateFile.close()
  edlFile.close()

def generateDeviceInputsEDL(edlFile, templateFile, deviceInputs, mpsName):
  data=templateFile.read()

  crates=[]
  cards=[]
  channels=[]
  byps=[]
  bypv=[]
  bypd=[]
  names=[]
  pvs=[]
  latched=[]
  unlatch=[]

  for deviceInput in deviceInputs:
    name = mpsName.getDeviceInputName(deviceInput)

    crates.append(deviceInput.channel.card.crate.number)
    cards.append(deviceInput.channel.card.number)
    channels.append(deviceInput.channel.number)
    byps.append('{0}_BYPS'.format(name))
    bypv.append('{0}_BYPV'.format(name))
    bypd.append('{0}_BYPD'.format(name))
    names.append(name)
    pvs.append('{0}_MPSC'.format(name))
    latched.append('{0}_MPS'.format(name))
    unlatch.append('{0}_UNLH'.format(name))
    
  nameSpace={'DEVICE_INPUTS': str(len(deviceInputs)),
             'DI_CRATE': crates,
             'DI_CARD': cards,
             'DI_CHANNEL': channels,
             'DI_BYPS': byps,
             'DI_BYPV': bypv,
             'DI_BYPD': bypd,
             'DI_NAME': names,
             'DI_PV': pvs,
             'DI_PV_LATCHED': latched,
             'DI_PV_UNLATCH': unlatch,
             }

  t = Template(data, searchList=[nameSpace])
  edlFile.write("%s" % t)
  templateFile.close()
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

parser.add_argument('--faults-edl', metavar='file', type=argparse.FileType('w'), nargs='?',
                    help='epics template file name for faults (e.g. faults.edl)')
parser.add_argument('--faults-template', metavar='file', type=argparse.FileType('r'), nargs='?',
                    help='Cheetah template file name for faults (e.g. faults.tmpl)')

args = parser.parse_args()

mps = MPSConfig(args.database[0].name)
session = mps.session
mpsName = MpsName(session)

if (args.device_inputs_edl and args.device_inputs_template):
  generateDeviceInputsEDL(args.device_inputs_edl, args.device_inputs_template,
                          session.query(models.DeviceInput).all(), mpsName)

if (args.analog_devices_edl and args.analog_devices_template):
  generateAnalogDevicesEDL(args.analog_devices_edl, args.analog_devices_template,
                           session.query(models.AnalogDevice).all(), mpsName)

if (args.faults_edl and args.faults_template):
  generateFaultsEDL(args.faults_edl, args.faults_template,
                    session.query(models.Fault).all(), mpsName)

session.close()

