#!/usr/bin/env python
#
# export_pydm.py
#
# Generates a text file with information about digital/analog inputs
# for PyDM displays.
#
# Examples
# --------
#
#   Digital Inputs for application card 2:
#   $ ./export_pvs.py --device-inputs list.txt --app-id 2 mps_gun_config.db
#
#   Analog Devices for application card 2:
#  $ ./export_pvs.py --analog-devices list.txt --app-id 2 mps_gun_config.db
#
#===============================================================================

from mps_database.mps_config import MPSConfig, models
from mps_database.tools.mps_names import MpsName
from sqlalchemy import func
import sys
import argparse

def dumpDeviceInputPVs(mpsName, pvFile):
  deviceInputs = session.query(models.DeviceInput).all()
  pvFile.write("# Channel Name | Crate Number | Card Number | Channel Number | PV\n")
  for device in deviceInputs:
    print((mpsName.getDeviceInputName(device)))
    pvFile.write(device.channel.name + "|" +
                 str(device.channel.card.crate.number) + "|" +
                 str(device.channel.card.number) + "|" +
                 str(device.channel.number) + "|" +
                 mpsName.getDeviceInputName(device) + "\n")

def dumpAnalogDeviceBasePVs(mpsName, pvFile):
  analogDevices = session.query(models.AnalogDevice).all()
  for device in analogDevices:
    print((mpsName.getAnalogDeviceName(device)))
    pvFile.write(mpsName.getAnalogDeviceName(device) + "\n")

def dumpAnalogDevicePVs(mpsName, pvFile):
  analogDevices = session.query(models.AnalogDevice).all()
  for device in analogDevices:
    faultInputs = session.query(models.FaultInput).filter(models.FaultInput.device_id==device.id).all()
    for fi in faultInputs:
      faults = session.query(models.Fault).filter(models.Fault.id==fi.fault_id).all()
      for fa in faults:
        faultStates = session.query(models.FaultState).filter(models.FaultState.fault_id==fa.id).all()
        for state in faultStates:
          print((mpsName.getAnalogDeviceName(device) + "_" + state.device_state.name))
          pvFile.write(device.name + " " + state.device_state.name + "|" +
                       str(device.channel.card.crate.number) + "|" +
                       str(device.channel.card.number) + "|" +
                       str(device.channel.number) + "|" +
                       mpsName.getAnalogDeviceName(device) + ":" + state.device_state.name + "\n")


def dumpFaultPVs(mpsName, pvFile):
  faults = session.query(models.Fault).all()
  for fault in faults:
    pvFile.write(mpsName.getFaultName(fault) + "|" + fault.description + "\n")

#=== MAIN ==================================================================================

parser = argparse.ArgumentParser(description='Export PV information for PyDM screens')
parser.add_argument('database', metavar='db', type=file, nargs=1, 
                    help='database file name (e.g. mps_gun.db)')
parser.add_argument('--device-inputs', metavar='file', type=argparse.FileType('w'), nargs='?',
                    help='list of PV names for digital channels (e.g. device_inputs.pv)')
parser.add_argument('--analog-devices', metavar='file', type=argparse.FileType('w'), nargs='?',
                    help='list of PV names for analog channels (e.g. analog_devices.pv)')
#parser.add_argument('--app-id', metavar='number', type=int, nargs=1, help='Application ID')
parser.add_argument('--faults', metavar='file', type=argparse.FileType('w'), nargs='?',
                    help='Fault PV information for faults')

args = parser.parse_args()

mps = MPSConfig(args.database[0].name)
#id = args.app_id[0]
session = mps.session

#print "Generating PVs for application " + str(id)

mpsName = MpsName(session)

if (args.device_inputs):
  dumpDeviceInputPVs(mpsName, args.device_inputs)

if (args.analog_devices):
  dumpAnalogDevicePVs(mpsName, args.analog_devices)

if (args.faults):
  dumpFaultPVs(mpsName, args.faults)

session.close()

