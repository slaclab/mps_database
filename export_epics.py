from mps_config import MPSConfig, models
from sqlalchemy import func
import sys
import argparse

#
# Sample Digital Channel record:
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

def exportDeviceInputs(file, deviceInputs):
  for deviceInput in deviceInputs:
    fields=[]
    fields.append(('DESC', 'Crate[{0}], Card[{1}], Channel[{2}]'.
                   format(deviceInput.channel.card.crate.number,
                          deviceInput.channel.card.number,
                          deviceInput.channel.number)))
    fields.append(('DTYP', 'asynInt32'))
    fields.append(('SCAN', '1 second'))
    fields.append(('ZNAM', 'OK'))
    fields.append(('ONAM', 'FAULTED'))
    fields.append(('INP', '@asyn(CENTRAL_NODE {0} 0)DEVICE_INPUT'.format(deviceInput.id)))
    printRecord(file, 'bi', '$(BASE):{0}'.format(deviceInput.channel.name), fields)
  file.close()

#
# Create one bi record for each device state for each analog device
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
      fields.append(('ZNAM', 'OK'))
      fields.append(('ONAM', 'FAULTED'))
      fields.append(('INP', '@asynMask(CENTRAL_NODE {0} {1} 0)ANALOG_DEVICE'.format(analogDevice.id, state.value)))
      printRecord(file, 'bi', '$(BASE):{0}_{1}'.format(analogDevice.channel.name, state.name), fields)
    
  file.close()

#=== MAIN ==================================================================================

parser = argparse.ArgumentParser(description='Export EPICS template database')
parser.add_argument('database', metavar='db', type=file, nargs=1, help='database file name (e.g. mps_gun.db)')
parser.add_argument('--device-inputs', metavar='file', type=argparse.FileType('w'), nargs='?', help='epics template file name for digital channels (e.g. device-inputs.template)')
parser.add_argument('--analog-devices', metavar='file', type=argparse.FileType('w'), nargs='?', help='epics template file name for analog channels (e.g. analog-devices.template)')

args = parser.parse_args()

mps = MPSConfig(args.database[0].name)
session = mps.session

if (args.device_inputs):
  exportDeviceInputs(args.device_inputs, session.query(models.DeviceInput).all())

if (args.analog_devices):
  exportAnalogDevices(args.analog_devices, session.query(models.AnalogDevice).all())

session.close()

