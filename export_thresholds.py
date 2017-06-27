#!/usr/bin/env python

from mps_config import MPSConfig, models
from sqlalchemy import func, exc
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

def getAnalogDeviceName(session, analogDevice):
  deviceType = session.query(models.DeviceType).filter(models.DeviceType.id==analogDevice.device_type_id).one()

  return deviceType.name + ":" + analogDevice.area + ":" + str(analogDevice.position)

#
# Create one bi record for each device state for each analog device
#
# For example, the BPMs have threshold bits for X, Y and TMIT. Each
# one of them has a bit mask to identify the fault. The mask
# is passed to asyn as the third parameter within the 
# '@asynMask(PORT ADDR MASK TIMEOUT)' INP record field
#
def exportAnalogThresholds(file, analogDevices, session):
  for analogDevice in analogDevices:
    name = getAnalogDeviceName(session, analogDevice)
    
    # All these queries are to get the threshold faults
    faultInputs = session.query(models.FaultInput).filter(models.FaultInput.device_id==analogDevice.id).all()
    for fi in faultInputs:
      faults = session.query(models.Fault).filter(models.Fault.id==fi.fault_id).all()
      for fa in faults:
        faultStates = session.query(models.FaultState).filter(models.FaultState.fault_id==fa.id).all()
        for state in faultStates:
          fields=[]
          fields.append(('DESC', 'High analog threshold for {0}'.
                         format(state.device_state.name)))
          fields.append(('DTYP', 'asynFloat64'))
          fields.append(('OUT', '@asynMask(LINK_NODE {0} {1} 0)ANALOG_THRESHOLD'.format(analogDevice.channel.number, state.device_state.mask)))
          printRecord(file, 'ao', '{0}:{1}_HIHI'.format(name, state.device_state.name), fields)

          fields=[]
          fields.append(('DESC', 'Low analog threshold for {0}'.
                         format(state.device_state.name)))
          fields.append(('DTYP', 'asynFloat64'))
          fields.append(('OUT', '@asynMask(LINK_NODE {0} {1} 0)ANALOG_THRESHOLD'.format(analogDevice.channel.number, state.device_state.mask)))
          printRecord(file, 'ao', '{0}:{1}_LOLO'.format(name, state.device_state.name), fields)
    

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
parser.add_argument('--app-id', metavar='number', type=int, nargs=1, help='Application ID')

parser.add_argument('--threshold-file', metavar='file', type=argparse.FileType('w'), nargs='?', 
                    help='epics template file name for analog thresholds (e.g. threshold.template)')

args = parser.parse_args()

mps = MPSConfig(args.database[0].name)
id = args.app_id[0]
session = mps.session

try:
  appCard = session.query(models.ApplicationCard).filter(models.ApplicationCard.id==id).one()
except exc.SQLAlchemyError:
  print "ERROR: no application card with id " + str(id) + " found. Exiting..."
  session.close()
  exit(-1)

if len(appCard.analog_channels) == 0:
  print "ERROR: no analog channels defined for application card " + str(id) + " (name=" + \
      appCard.name + ", description=" + appCard.description + "). Exiting..."
  session.close()
  exit(-1)

analogDevices = []
for channel in appCard.analog_channels:
  analogDevices.append(channel.analog_device)

exportAnalogThresholds(args.threshold_file, analogDevices, session)

session.close()

