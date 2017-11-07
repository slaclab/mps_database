#!/usr/bin/env python

from mps_config import MPSConfig, models
from mps_names import MpsName
from sqlalchemy import func
import sys
import argparse

#
# Sample Device Input (i.e. Digital Channel) record:
#
# record(bi, "CentralNode:DIGIN0") {
#     field(DESC, "Test input")
#     field(DTYP, "asynInt32")
#     field(SCAN, "1 second")
#     field(ZNAM, "OK")
#     field(ONAM, "FAULTED")
#     field(INP, "@asyn(CENTRAL_NODE 0 3)DIGITAL_CHANNEL")
#}

def printRecord(file, recType, recName, fields):
  file.write("record({0}, \"{1}\") {{\n".format(recType, recName))
  for name, value in fields:
    file.write("  field({0}, \"{1}\")\n".format(name, value))
  file.write("}\n\n")

#def getDeviceInputName(session, deviceInput):
#  digitalChannel = session.query(models.DigitalChannel).filter(models.DigitalChannel.id==deviceInput.channel_id).one()
#  device = session.query(models.DigitalDevice).filter(models.DigitalDevice.id==deviceInput.digital_device_id).one()
#  deviceType = session.query(models.DeviceType).filter(models.DeviceType.id==device.device_type_id).one()
#
#  return deviceType.name + ":" + device.area + ":" + str(device.position) + ":" + digitalChannel.name

#def getAnalogDeviceName(session, analogDevice):
#  deviceType = session.query(models.DeviceType).filter(models.DeviceType.id==analogDevice.device_type_id).one()
#
#  return deviceType.name + ":" + analogDevice.area + ":" + str(analogDevice.position)

#
# Create one bi record for each device input (digital device)
# Also creates:
#  ${DEV}_LATCHED
#  ${DEV}_BYPV (bypass value)
#  ${DEV}_BYPS (bypass status)
#  ${DEV}_BYPEXP (bypass expiration date?)
#
def exportDeviceInputs(file, deviceInputs, session):
  mpsName = MpsName(session)
  for deviceInput in deviceInputs:
#    name = getDeviceInputName(session, deviceInput)
    name = mpsName.getDeviceInputName(deviceInput)
    fields=[]
    fields.append(('DESC', 'CR[{0}], CA[{1}], CH[{2}]'.
                   format(deviceInput.channel.card.crate.number,
                          deviceInput.channel.card.number,
                          deviceInput.channel.number)))
    fields.append(('DTYP', 'asynUInt32Digital'))
    fields.append(('SCAN', '1 second'))
    fields.append(('ZNAM', '{0}'.format(deviceInput.channel.z_name)))
    fields.append(('ONAM', '{0}'.format(deviceInput.channel.o_name)))
    if deviceInput.channel.alarm_state == 0:
      fields.append(('ZSV', 'MAJOR'))
      fields.append(('OSV', 'NO_ALARM'))
    else:
      fields.append(('ZSV', 'NO_ALARM'))
      fields.append(('OSV', 'MAJOR'))

    fields.append(('INP', '@asynMask(CENTRAL_NODE {0} 1 0)MPS_DEVICE_INPUT'.format(deviceInput.id)))
    printRecord(file, 'bi', '{0}_MPSC'.format(name), fields)

    #=== Begin Latch records ====
    # Record for latched value
    fields[0]=(('DESC', 'CR[{0}], CA[{1}], CH[{2}] Latched Value'.
                format(deviceInput.channel.card.crate.number,
                       deviceInput.channel.card.number,
                       deviceInput.channel.number)))
    fields[7]=(('INP', '@asynMask(CENTRAL_NODE {0} 1 0)MPS_DEVICE_INPUT_LATCHED'.format(deviceInput.id)))
    printRecord(file, 'bi', '{0}_MPS'.format(name), fields)

    # Record to process unlatch value
    fields=[]
    fields.append(('DESC', 'CR[{0}], CA[{1}], CH[{2}] Unlatch'.
                   format(deviceInput.channel.card.crate.number,
                          deviceInput.channel.card.number,
                          deviceInput.channel.number)))
    fields.append(('DTYP', 'asynUInt32Digital'))
    fields.append(('OUT', '@asynMask(CENTRAL_NODE {0} 1 0)MPS_DEVICE_INPUT_UNLATCH'.format(deviceInput.id)))
    printRecord(file, 'bo', '{0}_UNLH'.format(name), fields)
    #=== End Latch records ====

    #=== Begin Bypass records ====
    # Bypass Value: used while bypass is active
    fields=[]
    fields.append(('DESC', 'Bypass Value'))
    fields.append(('DTYP', 'asynUInt32Digital'))
    fields.append(('ZNAM', '{0}'.format(deviceInput.channel.z_name)))
    fields.append(('ONAM', '{0}'.format(deviceInput.channel.o_name)))
    if deviceInput.channel.alarm_state == 0:
      fields.append(('ZSV', 'MAJOR'))
      fields.append(('OSV', 'NO_ALARM'))
    else:
      fields.append(('ZSV', 'NO_ALARM'))
      fields.append(('OSV', 'MAJOR'))
    fields.append(('OUT', '@asynMask(CENTRAL_NODE {0} 1 0)MPS_DEVICE_INPUT_BYPV'.format(deviceInput.id)))
    fields.append(('VAL', '0'))
    fields.append(('PINI', 'YES'))
    printRecord(file, 'bo', '{0}_BYPV'.format(name), fields)

    # Bypass Status: shows if bypass is currently active or not
    fields=[]
    fields.append(('DESC', 'Bypass Status'))
    fields.append(('SCAN', '1 second'))
    fields.append(('DTYP', 'asynUInt32Digital'))    
    fields.append(('ZNAM', 'Not Bypassed'))
    fields.append(('ONAM', 'Bypassed'))
    fields.append(('ZSV', 'NO_ALARM'))
    fields.append(('OSV', 'MAJOR'))
    fields.append(('INP', '@asynMask(CENTRAL_NODE {0} 1 0)MPS_DEVICE_INPUT_BYPS'.format(deviceInput.id)))
    printRecord(file, 'bi', '{0}_BYPS'.format(name), fields)

    # Bypass Expiration Date: date/time in seconds since Unix epoch for bypass expiration
    fields=[]
    fields.append(('DESC', 'Bypass duration in seconds'))
    fields.append(('DTYP', 'asynInt32'))
    fields.append(('EGU', 'Seconds'))
    fields.append(('VAL', '0'))
    fields.append(('PINI', 'YES'))
    fields.append(('OUT', '@asyn(CENTRAL_NODE {0} 0)MPS_DEVICE_INPUT_BYPEXPDATE'.format(deviceInput.id)))
    printRecord(file, 'longout', '{0}_BYPD'.format(name), fields)

    fields=[]
    fields.append(('DESC', 'Remaining bypass duration is seconds'))
    fields.append(('DTYP', 'asynInt32'))
    fields.append(('EGU', 'Seconds'))
    fields.append(('SCAN', '1 second'))
    fields.append(('VAL', '0'))
    fields.append(('PINI', 'YES'))
    fields.append(('INP', '@asyn(CENTRAL_NODE {0} 0)MPS_DEVICE_INPUT_REMAINING_BYPTIME'.format(deviceInput.id)))
    printRecord(file, 'longin', '{0}_BYPT'.format(name), fields)

    fields=[]
    fields.append(('DESC', 'Bypass Expiration Date/Time String'))
    fields.append(('DTYP', 'asynOctetRead'))
    fields.append(('SCAN', '1 second'))
    fields.append(('VAL', 'Invalid'))
    fields.append(('PINI', 'YES'))
    fields.append(('INP', '@asyn(CENTRAL_NODE {0} 0)MPS_DEVICE_INPUT_BYPEXPDATE_STRING'.format(deviceInput.id)))
    printRecord(file, 'stringin', '{0}_BYPD_STR'.format(name), fields)
    #=== End Bypass records ====

  file.close()

#
# Create one bi record for each device state for each analog device
#
# For example, the BPMs have threshold bits for X, Y and TMIT. Each
# one of them has a bit mask to identify the fault. The mask
# is passed to asyn as the third parameter within the 
# '@asynMask(PORT ADDR MASK TIMEOUT)' INP record field
#
def exportAnalogDevices(file, analogDevices, session):
  mpsName = MpsName(session)
  for analogDevice in analogDevices:
#    name = getAnalogDeviceName(session, analogDevice)
    name = mpsName.getAnalogDeviceName(analogDevice)
#    print name
    
    # All these queries are to get the threshold faults
    faultInputs = session.query(models.FaultInput).filter(models.FaultInput.device_id==analogDevice.id).all()
    for fi in faultInputs:
      faults = session.query(models.Fault).filter(models.Fault.id==fi.fault_id).all()
      for fa in faults:
        # produce only one set of bypass pvs per analog fault (one bypass control for all thresholds within an integrator)
        bypassPvs=False 
        print fa.name
        faultStates = session.query(models.FaultState).filter(models.FaultState.fault_id==fa.id).all()
        for state in faultStates:
#          print state.device_state.name
          bitIndex=0
          bitFound=False
          while not bitFound:
            b=(state.device_state.mask>>bitIndex) & 1
            if b==1:
              bitFound=True
            else:
              bitIndex=bitIndex+1
              if bitIndex==32:
                done=True
                bitIndex=-1
          if bitIndex==-1:
            print "ERROR: invalid threshold mask (" + hex(state.device_state.mask)
            exit(-1)

          # Convert bitIndex to integrator index
          # BPM: bit 0-7 -> X, bit 8-15 -> Y, bit 16-23 -> TMIT
          # Non-BPM: bit 0-7 -> INT0, bit 8-15 -> INT1, bit 16-23 -> INT2, bit 24-31 -> INT3
          intIndex=0
          if (bitIndex >= 8 and bitIndex <= 15):
            intIndex = 1
          elif (bitIndex >= 16 and bitIndex <= 23):
            intIndex = 2
          elif (bitIndex >= 24 and bitIndex <= 31):
            intIndex = 3

          print name + ":" + state.device_state.name + ", mask: " + str(bitIndex) + ", fault name: " + fa.name + ", intIndex: " + str(intIndex)
          fields=[]
          fields.append(('DESC', 'Crate[{0}], Card[{1}], Channel[{2}]'.
                         format(analogDevice.channel.card.crate.number,
                                analogDevice.channel.card.number,
                                analogDevice.channel.number)))
          fields.append(('DTYP', 'asynUInt32Digital'))
          fields.append(('SCAN', '1 second'))
          fields.append(('ZNAM', 'IS_OK'))
          fields.append(('ONAM', 'IS_EXCEEDED'))
          fields.append(('ZSV', 'NO_ALARM'))
          fields.append(('OSV', 'MAJOR'))
          fields.append(('INP', '@asynMask(CENTRAL_NODE {0} {1} 0)MPS_ANALOG_DEVICE'.format(analogDevice.id, state.device_state.mask)))
          printRecord(file, 'bi', '{0}:{1}_MPSC'.format(name, state.device_state.name), fields)
    
          #=== Begin Latch records ====
          # Record for latched value
          fields=[]
          fields.append(('DESC', 'CR[{0}], CA[{1}], CH[{2}] Latched Value'.
                         format(analogDevice.channel.card.crate.number,
                                analogDevice.channel.card.number,
                                analogDevice.channel.number)))
          fields.append(('DTYP', 'asynUInt32Digital'))
          fields.append(('SCAN', '1 second'))
          fields.append(('ZNAM', 'IS_OK'))
          fields.append(('ONAM', 'IS_EXCEEDED'))
          fields.append(('ZSV', 'NO_ALARM'))
          fields.append(('OSV', 'MAJOR'))
          fields.append(('INP', '@asynMask(CENTRAL_NODE {0} {1} 0)MPS_ANALOG_DEVICE_LATCHED'.format(analogDevice.id, state.device_state.mask)))
          printRecord(file, 'bi', '{0}:{1}_MPS'.format(name, state.device_state.name), fields)

          # Record to process unlatch value
          fields=[]
          fields.append(('DESC', 'CR[{0}], CA[{1}], CH[{2}] Unlatch'.
                         format(analogDevice.channel.card.crate.number,
                                analogDevice.channel.card.number,
                                analogDevice.channel.number)))
          fields.append(('DTYP', 'asynUInt32Digital'))
          fields.append(('OUT', '@asynMask(CENTRAL_NODE {0} {1} 0)MPS_ANALOG_DEVICE_UNLATCH'.format(analogDevice.id, state.device_state.mask)))
          printRecord(file, 'bo', '{0}:{1}_UNLH'.format(name, state.device_state.name), fields)
          #=== End Latch records ====

          #=== Begin Bypass records (One PV per fault type)  ====
          # produce only one set of bypass pvs per analog fault (one bypass control for all thresholds within an integrator)
          # there is no BYPV PV for analog devices
          if (bypassPvs==False):            
            # Bypass Status: shows if bypass is currently active or not
            fields=[]
            fields.append(('DESC', 'Bypass Status'))
            fields.append(('SCAN', '1 second'))
            fields.append(('DTYP', 'asynInt32'))    
            fields.append(('ZNAM', 'Not Bypassed'))
            fields.append(('ONAM', 'Bypassed'))
            fields.append(('ZSV', 'NO_ALARM'))
            fields.append(('OSV', 'MAJOR'))
            fields.append(('INP', '@asyn(CENTRAL_NODE {0} {1})MPS_ANALOG_DEVICE_BYPS'.format(analogDevice.id, intIndex)))
            printRecord(file, 'bi', '{0}:{1}_BYPS'.format(name, fa.name), fields)
          
            # Bypass Expiration Date: date/time in seconds since Unix epoch for bypass expiration
            fields=[]
            fields.append(('DESC', 'Bypass duration in seconds'))
            fields.append(('DTYP', 'asynInt32'))
            fields.append(('VAL', '0'))
            fields.append(('PINI', 'YES'))
            fields.append(('OUT', '@asyn(CENTRAL_NODE {0} {1})MPS_ANALOG_DEVICE_BYPEXPDATE'.format(analogDevice.id, intIndex)))
            printRecord(file, 'longout', '{0}:{1}_BYPD'.format(name, fa.name), fields)
            
            fields=[]
            fields.append(('DESC', 'Remaining bypass duration is seconds'))
            fields.append(('DTYP', 'asynInt32'))
            fields.append(('EGU', 'Seconds'))
            fields.append(('SCAN', '1 second'))
            fields.append(('VAL', '0'))
            fields.append(('PINI', 'YES'))
            fields.append(('INP', '@asyn(CENTRAL_NODE {0} {1})MPS_ANALOG_DEVICE_REMAINING_BYPTIME'.format(analogDevice.id, intIndex)))
            printRecord(file, 'longin', '{0}:{1}_BYPT'.format(name, fa.name), fields)

            fields=[]
            fields.append(('DESC', 'Bypass Expiration Date/Time String'))
            fields.append(('DTYP', 'asynOctetRead'))
            fields.append(('SCAN', '1 second'))
            fields.append(('VAL', 'Invalid'))
            fields.append(('PINI', 'YES'))
            fields.append(('INP', '@asyn(CENTRAL_NODE {0} 0)MPS_ANALOG_DEVICE_BYPEXPDATE_STRING'.format(analogDevice.id)))
            printRecord(file, 'stringin', '{0}:{1}_BYPD_STR'.format(name, fa.name), fields)

            fields=[]
            fields.append(('DESC', 'Ignored status'))
            fields.append(('DTYP', 'asynUInt32Digital'))
            fields.append(('SCAN', '1 second'))
            fields.append(('ZNAM', 'Not Ignored'))
            fields.append(('ONAM', 'Ignored'))
            fields.append(('ZSV', 'NO_ALARM'))
            fields.append(('OSV', 'MAJOR'))
            fields.append(('INP', '@asynMask(CENTRAL_NODE {0} 1 0)MPS_ANALOG_DEVICE_IGNORED'.format(analogDevice.id)))
            printRecord(file, 'bi', '{0}:{1}_IGN'.format(name, fa.name), fields)
            
            bypassPvs=True
          #=== End Bypass records ====
  file.close()

'''
# Bypass per threshold is not possible in HW - these PVs are not needed!
          #=== Begin Bypass records ====
          # Bypass Value: used while bypass is active
          fields=[]
          fields.append(('DESC', 'Bypass for {0}'.format(analogDevice.channel.name)))
          fields.append(('DTYP', 'asynUInt32Digital'))
          fields.append(('VAL', '0'))
          fields.append(('PINI', 'YES'))
          fields.append(('ZNAM', 'IS_OK'))
          fields.append(('ONAM', 'IS_EXCEEDED'))
          fields.append(('ZSV', 'NO_ALARM'))
          fields.append(('OSV', 'MAJOR'))
          fields.append(('OUT', '@asynMask(CENTRAL_NODE {0} 0 {1})MPS_ANALOG_DEVICE_BYPV'.format(analogDevice.id, bitIndex)))
          printRecord(file, 'bo', '{0}:{1}_BYPV'.format(name, state.device_state.name), fields)

          # Bypass Status: shows if bypass is currently active or not
          fields=[]
          fields.append(('DESC', 'Bypass Status'))
          fields.append(('SCAN', '1 second'))
          fields.append(('DTYP', 'asynInt32'))    
          fields.append(('ZNAM', 'Not Bypassed'))
          fields.append(('ONAM', 'Bypassed'))
          fields.append(('ZSV', 'NO_ALARM'))
          fields.append(('OSV', 'MAJOR'))
          fields.append(('INP', '@asyn(CENTRAL_NODE {0} {1})MPS_ANALOG_DEVICE_BYPS'.format(analogDevice.id, bitIndex)))
          printRecord(file, 'bi', '{0}:{1}_BYPS'.format(name, state.device_state.name), fields)

          # Bypass Expiration Date: date/time in seconds since Unix epoch for bypass expiration
          fields=[]
          fields.append(('DESC', 'Bypass Expiration Date/Time'))
          fields.append(('DTYP', 'asynInt32'))
          fields.append(('VAL', '0'))
          fields.append(('PINI', 'YES'))
          fields.append(('OUT', '@asyn(CENTRAL_NODE {0} {1})MPS_ANALOG_DEVICE_BYPEXPDATE'.format(analogDevice.id, bitIndex)))
          printRecord(file, 'longout', '{0}:{1}_BYPD'.format(name, state.device_state.name), fields)

          fields=[]
          fields.append(('DESC', 'Bypass Expiration Date/Time String'))
          fields.append(('DTYP', 'asynOctetRead'))
          fields.append(('SCAN', '1 second'))
          fields.append(('VAL', 'Invalid'))
          fields.append(('PINI', 'YES'))
          fields.append(('INP', '@asyn(CENTRAL_NODE {0} 0)MPS_ANALOG_DEVICE_BYPEXPDATE_STRING'.format(analogDevice.id)))
          printRecord(file, 'stringin', '{0}:{1}_BYPD_STR'.format(name, state.device_state.name), fields)
          #=== End Bypass records ====
'''

def exportMitigationDevices(file, mitigationDevices, beamClasses, session):
  mpsName = MpsName(session)

  fields=[]
  fields.append(('DESC', 'Total number of beam power classes'))
  fields.append(('PINI', 'YES'))
  fields.append(('VAL', '{0}'.format((len(beamClasses)))))
  printRecord(file, 'longout', '$(BASE):NUM_PC', fields)

  for beamClass in beamClasses:
    fields=[]
    fields.append(('DESC', '{0}'.format(beamClass.description)))
    fields.append(('PINI', 'YES'))
    fields.append(('VAL', '{0}'.format(beamClass.number)))
    printRecord(file, 'longout', '$(BASE):PC_{0}'.format(beamClass.number), fields)

  for mitigationDevice in mitigationDevices:
    name = mpsName.getMitigationDeviceName(mitigationDevice)

    fields=[]
    fields.append(('DESC', 'Software mitigation for: {0}'.format(mitigationDevice.name)))
    fields.append(('DTYP', 'asynInt32'))
    fields.append(('SCAN', '1 second'))
    fields.append(('INP', '@asyn(CENTRAL_NODE {0} 0)MPS_SW_MITIGATION'.format(mitigationDevice.id))) # former MITIGATION_DEVICE
    printRecord(file, 'longin', '$(BASE):{0}_SW_PC'.format(mitigationDevice.name.upper()), fields)
    
    fields=[]
    fields.append(('DESC', 'Fast mitigation for {0}'.format(mitigationDevice.name)))
    fields.append(('DTYP', 'asynInt32'))
    fields.append(('SCAN', '1 second'))
    fields.append(('INP', '@asyn(CENTRAL_NODE {0} 0)MPS_FW_MITIGATION'.format(mitigationDevice.id)))
    printRecord(file, 'longin', '$(BASE):{0}_FW_PC'.format(mitigationDevice.name.upper()), fields)

    fields=[]
    fields.append(('DESC', 'Current mitigation for {0}'.format(mitigationDevice.name)))
    fields.append(('DTYP', 'asynInt32'))
    fields.append(('SCAN', '1 second'))
    fields.append(('INP', '@asyn(CENTRAL_NODE {0} 0)MPS_MITIGATION'.format(mitigationDevice.id)))
    printRecord(file, 'longin', '$(BASE):{0}_PC'.format(mitigationDevice.name.upper()), fields)

    fields=[]
    fields.append(('DESC', 'Latched mitigation for {0}'.format(mitigationDevice.name)))
    fields.append(('DTYP', 'asynInt32'))
    fields.append(('SCAN', '1 second'))
    fields.append(('INP', '@asyn(CENTRAL_NODE {0} 0)MPS_LATCHED_MITIGATION'.format(mitigationDevice.id)))
    printRecord(file, 'longin', '$(BASE):{0}_LATCHED_PC'.format(mitigationDevice.name.upper()), fields)

  file.close()

def exportFaults(file, faults, session):
  mpsName = MpsName(session)
  for fault in faults:
    name = mpsName.getFaultName(fault)
    fields=[]
    fields.append(('DESC', '{0}'.format(fault.description)))
    fields.append(('DTYP', 'asynUInt32Digital'))
    fields.append(('SCAN', '1 second'))
    fields.append(('ZNAM', 'OK'))
    fields.append(('ONAM', 'FAULTED'))
    fields.append(('ZSV', 'NO_ALARM'))
    fields.append(('OSV', 'MAJOR'))
    fields.append(('INP', '@asynMask(CENTRAL_NODE {0} 1 0)MPS_FAULT'.format(fault.id)))
    printRecord(file, 'bi', '{0}'.format(name), fields)

    fields=[]
    fields.append(('DESC', '{0}'.format(fault.description)))
    fields.append(('DTYP', 'asynUInt32Digital'))
    fields.append(('SCAN', '1 second'))
    fields.append(('ZNAM', 'Not Ignored'))
    fields.append(('ONAM', 'Ignored'))
    fields.append(('ZSV', 'NO_ALARM'))
    fields.append(('OSV', 'MAJOR'))
    fields.append(('INP', '@asynMask(CENTRAL_NODE {0} 1 0)MPS_FAULT_IGNORED'.format(fault.id)))
    printRecord(file, 'bi', '{0}_IGN'.format(name), fields)

    fields=[]
    fields.append(('DESC', '{0}'.format(fault.description)))
    fields.append(('DTYP', 'asynUInt32Digital'))
    fields.append(('SCAN', '1 second'))
    fields.append(('ZNAM', 'OK'))
    fields.append(('ONAM', 'FAULTED'))
    fields.append(('ZSV', 'NO_ALARM'))
    fields.append(('OSV', 'MAJOR'))
    fields.append(('INP', '@asynMask(CENTRAL_NODE {0} 1 0)MPS_FAULT_LATCHED'.format(fault.id)))
    printRecord(file, 'bi', '{0}_MPS'.format(name), fields)

    fields=[]
    fields.append(('DESC', '{0}'.format(fault.description)))
    fields.append(('DTYP', 'asynUInt32Digital'))
    fields.append(('OUT', '@asynMask(CENTRAL_NODE {0} 1 0)MPS_FAULT_UNLATCH'.format(fault.id)))
    printRecord(file, 'bo', '{0}_UNLH'.format(name), fields)

  file.close()

def exportApps(file, apps, session):
#  mpsName = MpsName(session)
  for app in apps:
    crate = session.query(models.Crate).filter(models.Crate.id==app.crate_id).one()
#    name = mpsName.getFaultName(fault)
    fields=[]
    fields.append(('DESC', '{0} [{1}-{2}{3} S{4}]'.format(app.name, crate.location, crate.rack, crate.elevation, app.slot_number)))
    fields.append(('DTYP', 'asynUInt32Digital'))
    fields.append(('SCAN', '1 second'))
    fields.append(('ZNAM', 'OFFLINE'))
    fields.append(('ONAM', 'ONLINE'))
    fields.append(('ZSV', 'MAJOR'))
    fields.append(('OSV', 'NO_ALARM'))
    fields.append(('INP', '@asynMask(CENTRAL_NODE {0} 1 0)MPS_APP_STATUS'.format(app.id)))
    printRecord(file, 'bi', '$(BASE):APP{0}_STATUS'.format(app.id), fields)

  file.close()

#=== MAIN ==================================================================================

parser = argparse.ArgumentParser(description='Export EPICS template database')
parser.add_argument('database', metavar='db', type=file, nargs=1, 
                    help='database file name (e.g. mps_gun.db)')
parser.add_argument('--device-inputs', metavar='file', type=argparse.FileType('w'), nargs='?',
                    help='epics template file name for digital channels (e.g. device-inputs.template)')
parser.add_argument('--analog-devices', metavar='file', type=argparse.FileType('w'), nargs='?', 
                    help='epics template file name for analog channels (e.g. analog-devices.template)')
parser.add_argument('--mitigation-devices', metavar='file', type=argparse.FileType('w'), nargs='?', 
                    help='epics template file name for mitigation devices and beam classes (e.g. mitigation.template)')
parser.add_argument('--faults', metavar='file', type=argparse.FileType('w'), nargs='?', 
                    help='epics template file name for faults (e.g. faults.template)')
parser.add_argument('--apps', metavar='file', type=argparse.FileType('w'), nargs='?',
                    help='epics template file name for application cards (e.g. apps.template)')

args = parser.parse_args()

mps = MPSConfig(args.database[0].name)
session = mps.session

if (args.device_inputs):
  exportDeviceInputs(args.device_inputs, session.query(models.DeviceInput).all(), session)

if (args.analog_devices):
  exportAnalogDevices(args.analog_devices, session.query(models.AnalogDevice).all(), session)

if (args.mitigation_devices):
  exportMitigationDevices(args.mitigation_devices,
                          session.query(models.MitigationDevice).all(),
                          session.query(models.BeamClass).all(), session)

if (args.faults):
  exportFaults(args.faults, session.query(models.Fault).all(), session)

if (args.apps):
  exportApps(args.apps, session.query(models.ApplicationCard).all(), session)

session.close()

