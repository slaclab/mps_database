from mps_config import MPSConfig, models
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

#
# Create one bi record for each device input (digital device)
# Also creates:
#  ${DEV}_LATCHED
#  ${DEV}_BYPV (bypass value)
#  ${DEV}_BYPS (bypass status)
#  ${DEV}_BYPEXP (bypass expiration date?)
#
def exportDeviceInputs(file, deviceInputs):
  for deviceInput in deviceInputs:
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

    fields.append(('INP', '@asynMask(CENTRAL_NODE {0} 1 0)DEVICE_INPUT'.format(deviceInput.id)))
    printRecord(file, 'bi', '$(BASE):{0}'.format(deviceInput.channel.name), fields)

    #=== Begin Latch records ====
    # Record for latched value
    fields[0]=(('DESC', 'CR[{0}], CA[{1}], CH[{2}] Latched Value'.
                format(deviceInput.channel.card.crate.number,
                       deviceInput.channel.card.number,
                       deviceInput.channel.number)))
    fields[7]=(('INP', '@asynMask(CENTRAL_NODE {0} 1 0)DEVICE_INPUT_LATCHED'.format(deviceInput.id)))
    printRecord(file, 'bi', '$(BASE):{0}_LATCHED'.format(deviceInput.channel.name), fields)

    # Record to process unlatch value
    fields=[]
    fields.append(('DESC', 'CR[{0}], CA[{1}], CH[{2}] Unlatch'.
                   format(deviceInput.channel.card.crate.number,
                          deviceInput.channel.card.number,
                          deviceInput.channel.number)))
    fields.append(('DTYP', 'asynUInt32Digital'))
    fields.append(('OUT', '@asynMask(CENTRAL_NODE {0} 1 0)DEVICE_INPUT_UNLATCH'.format(deviceInput.id)))
    printRecord(file, 'bo', '$(BASE):{0}_UNLATCH'.format(deviceInput.channel.name), fields)
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
    fields.append(('OUT', '@asynMask(CENTRAL_NODE {0} 1 0)DEVICE_INPUT_BYPV'.format(deviceInput.id)))
    fields.append(('VAL', '0'))
    fields.append(('PINI', 'YES'))
    printRecord(file, 'bo', '$(BASE):{0}_BYPV'.format(deviceInput.channel.name), fields)

    # Bypass Status: shows if bypass is currently active or not
    fields=[]
    fields.append(('DESC', 'Bypass Status'))
    fields.append(('SCAN', '1 second'))
    fields.append(('DTYP', 'asynUInt32Digital'))    
    fields.append(('ZNAM', 'Not Bypassed'))
    fields.append(('ONAM', 'Bypassed'))
    fields.append(('ZSV', 'NO_ALARM'))
    fields.append(('OSV', 'MAJOR'))
    fields.append(('INP', '@asynMask(CENTRAL_NODE {0} 1 0)DEVICE_INPUT_BYPS'.format(deviceInput.id)))
    printRecord(file, 'bi', '$(BASE):{0}_BYPS'.format(deviceInput.channel.name), fields)

    # Bypass Expiration Date: date/time in seconds since Unix epoch for bypass expiration
    fields=[]
    fields.append(('DESC', 'Bypass Expiration Date/Time'))
    fields.append(('DTYP', 'asynInt32'))
    fields.append(('EGU', 'Seconds'))
    fields.append(('VAL', '0'))
    fields.append(('PINI', 'YES'))
    fields.append(('OUT', '@asyn(CENTRAL_NODE {0} 0)DEVICE_INPUT_BYPEXPDATE'.format(deviceInput.id)))
    printRecord(file, 'longout', '$(BASE):{0}_BYPEXPDATE'.format(deviceInput.channel.name), fields)

    fields=[]
    fields.append(('DESC', 'Bypass Expiration Date/Time String'))
    fields.append(('DTYP', 'asynOctetRead'))
    fields.append(('SCAN', '1 second'))
    fields.append(('VAL', 'Invalid'))
    fields.append(('PINI', 'YES'))
    fields.append(('INP', '@asyn(CENTRAL_NODE {0} 0)DEVICE_INPUT_BYPEXPDATE_STRING'.format(deviceInput.id)))
    printRecord(file, 'stringin', '$(BASE):{0}_BYPEXPDATE_STR'.format(deviceInput.channel.name), fields)
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
def exportAnalogDevices(file, analogDevices):
  for analogDevice in analogDevices:
    for state in analogDevice.device_type.states:
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
      fields.append(('INP', '@asynMask(CENTRAL_NODE {0} {1} 0)ANALOG_DEVICE'.format(analogDevice.id, state.mask)))
      printRecord(file, 'bi', '$(BASE):{0}_{1}'.format(analogDevice.channel.name, state.name), fields)
    
    #=== Begin Latch records ====
    # Record for latched value
    fields=[]
    fields.append(('DESC', 'CR[{0}], CA[{1}], CH[{2}] Latched Value'.
                   format(analogDevice.channel.card.crate.number,
                          analogDevice.channel.card.number,
                          analogDevice.channel.number)))
    fields.append(('DTYP', 'asynInt32'))
    fields.append(('ZSV', 'NO_ALARM')) # when 0 there is no threshold faults
    fields.append(('OSV', 'MAJOR'))
    fields.append(('SCAN', '1 second'))
    fields.append(('INP', '@asyn(CENTRAL_NODE {0} 1)ANALOG_DEVICE_LATCHED'.format(analogDevice.id)))
    printRecord(file, 'longin', '$(BASE):{0}_LATCHED'.format(analogDevice.channel.name), fields)

    # Record to process unlatch value
    fields=[]
    fields.append(('DESC', 'CR[{0}], CA[{1}], CH[{2}] Unlatch'.
                   format(analogDevice.channel.card.crate.number,
                          analogDevice.channel.card.number,
                          analogDevice.channel.number)))
    fields.append(('DTYP', 'asynUInt32Digital'))
    fields.append(('OUT', '@asynMask(CENTRAL_NODE {0} 1 0)ANALOG_DEVICE_UNLATCH'.format(analogDevice.id)))
    printRecord(file, 'bo', '$(BASE):{0}_UNLATCH'.format(analogDevice.channel.name), fields)
    #=== End Latch records ====

    #=== Begin Bypass records ====
    # Bypass Value: used while bypass is active
    fields=[]
    fields.append(('DESC', 'Threshold bypass value for {0}'.format(analogDevice.channel.name)))
    fields.append(('DTYP', 'asynInt32'))
    fields.append(('VAL', '0'))
    fields.append(('PINI', 'YES'))
    fields.append(('ZSV', 'NO_ALARM')) # when 0 there is no threshold faults
    fields.append(('OSV', 'MAJOR'))
    fields.append(('OUT', '@asyn(CENTRAL_NODE {0} 0)ANALOG_DEVICE_BYPV'.format(analogDevice.id)))
    printRecord(file, 'longout', '$(BASE):{0}_BYPV'.format(analogDevice.channel.name), fields)

    # Bypass Status: shows if bypass is currently active or not
    fields=[]
    fields.append(('DESC', 'Bypass Status'))
    fields.append(('SCAN', '1 second'))
    fields.append(('DTYP', 'asynUInt32Digital'))    
    fields.append(('ZNAM', 'Not Bypassed'))
    fields.append(('ONAM', 'Bypassed'))
    fields.append(('ZSV', 'NO_ALARM'))
    fields.append(('OSV', 'MAJOR'))
    fields.append(('INP', '@asynMask(CENTRAL_NODE {0} 1 0)ANALOG_DEVICE_BYPS'.format(analogDevice.id)))
    printRecord(file, 'bi', '$(BASE):{0}_BYPS'.format(analogDevice.channel.name), fields)

    # Bypass Expiration Date: date/time in seconds since Unix epoch for bypass expiration
    fields=[]
    fields.append(('DESC', 'Bypass Expiration Date/Time'))
    fields.append(('DTYP', 'asynInt32'))
    fields.append(('VAL', '0'))
    fields.append(('PINI', 'YES'))
    fields.append(('OUT', '@asyn(CENTRAL_NODE {0} 0)ANALOG_DEVICE_BYPEXPDATE'.format(analogDevice.id)))
    printRecord(file, 'longout', '$(BASE):{0}_BYPEXPDATE'.format(analogDevice.channel.name), fields)

    fields=[]
    fields.append(('DESC', 'Bypass Expiration Date/Time String'))
    fields.append(('DTYP', 'asynOctetRead'))
    fields.append(('SCAN', '1 second'))
    fields.append(('VAL', 'Invalid'))
    fields.append(('PINI', 'YES'))
    fields.append(('INP', '@asyn(CENTRAL_NODE {0} 0)ANALOG_DEVICE_BYPEXPDATE_STRING'.format(analogDevice.id)))
    printRecord(file, 'stringin', '$(BASE):{0}_BYPEXPDATE_STR'.format(analogDevice.channel.name), fields)
    #=== End Bypass records ====

  file.close()

def exportMitiagationDevices(file, mitigationDevices, beamClasses):
  fields=[]
  fields.append(('DESC', 'Number of beam classes'))
  fields.append(('PINI', 'YES'))
  fields.append(('VAL', '{0}'.format((len(beamClasses)))))
  printRecord(file, 'longout', '$(BASE):NUM_BEAM_CLASSES', fields)

  for beamClass in beamClasses:
    fields=[]
    fields.append(('DESC', '{0}'.format(beamClass.description)))
    fields.append(('PINI', 'YES'))
    fields.append(('VAL', '{0}'.format(beamClass.number)))
    printRecord(file, 'longout', '$(BASE):BEAM_CLASS_{0}'.format(beamClass.number), fields)

  for mitigationDevice in mitigationDevices:
    fields=[]
    fields.append(('DESC', 'Mitigation Device: {0}'.format(mitigationDevice.name)))
    fields.append(('DTYP', 'asynInt32'))
    fields.append(('SCAN', '1 second'))
    fields.append(('INP', '@asyn(CENTRAL_NODE {0} 0)MITIGATION_DEVICE'.format(mitigationDevice.id)))
    printRecord(file, 'ai', '$(BASE):{0}_ALLOWED_CLASS'.format(mitigationDevice.name.upper()), fields)
    

  file.close()

def exportFaults(file, faults):
  for fault in faults:
    fields=[]
    fields.append(('DESC', '{0}'.format(fault.description)))
    fields.append(('DTYP', 'asynUInt32Digital'))
    fields.append(('SCAN', '1 second'))
    fields.append(('ZNAM', 'OK'))
    fields.append(('ONAM', 'FAULTED'))
    fields.append(('INP', '@asynMask(CENTRAL_NODE {0} 1 0)FAULT'.format(fault.id)))
    printRecord(file, 'bi', '$(BASE):{0}'.format(fault.name), fields)

    fields=[]
    fields.append(('DESC', '{0} (ignore)'.format(fault.description)))
    fields.append(('DTYP', 'asynUInt32Digital'))
    fields.append(('SCAN', '1 second'))
    fields.append(('ZNAM', 'Not Ignored'))
    fields.append(('ONAM', 'Ignored'))
    fields.append(('INP', '@asynMask(CENTRAL_NODE {0} 1 0)FAULT_IGNORED'.format(fault.id)))
    printRecord(file, 'bi', '$(BASE):{0}_IGNORED'.format(fault.name), fields)

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

args = parser.parse_args()

mps = MPSConfig(args.database[0].name)
session = mps.session

if (args.device_inputs):
  exportDeviceInputs(args.device_inputs, session.query(models.DeviceInput).all())

if (args.analog_devices):
  exportAnalogDevices(args.analog_devices, session.query(models.AnalogDevice).all())

if (args.mitigation_devices):
  exportMitiagationDevices(args.mitigation_devices,
                           session.query(models.MitigationDevice).all(),
                           session.query(models.BeamClass).all())

if (args.faults):
  exportFaults(args.faults, session.query(models.Fault).all())

session.close()

