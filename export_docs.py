#!/usr/bin/env python

from mps_config import MPSConfig, models
import sys
import argparse

def writeHeader(f):
  f.write('<!DOCTYPE book PUBLIC "-//OASIS//DTD DocBook V3.1//EN">\n')

  f.write('<book>\n')
  f.write('\n')
  f.write('<bookinfo>\n')
  f.write('   <title>MpsDatabase</title>\n')
  f.write('   <author>\n')
  f.write('     <firstname>L.</firstname><surname>Piccoli</surname>\n')
  f.write('   </author>\n')
  f.write('</bookinfo>\n')

def writeMitigationTableHeader(f, session):
  f.write('  <entry>Fault Name</entry>\n')
  mitDevices={}
  mitigationDevices = session.query(models.MitigationDevice).\
      order_by(models.MitigationDevice.destination_mask.desc())
  for mit in mitigationDevices:
    mitDevices[mit.name] = '-'
    f.write('  <entry>{0}</entry>\n'.format(mit.name))

  return mitDevices

def writeMitigationTableRows(f, faultName, mitigationDevices):
  f.write('  <entry>{0}</entry>\n'.format(faultName))
  for key in mitigationDevices:
    f.write('  <entry>{0}</entry>\n'.format(mitigationDevices[key]))


def writeDigitalFault(f, fault, device, session):
  channelName = []
  channelCrate = []
  channelSlot = []
  channelNumber = []

  num_bits = 0
  for ddi in device.inputs:
    channel = session.query(models.DigitalChannel).\
        filter(models.DigitalChannel.id==ddi.channel_id).one()
    card = session.query(models.ApplicationCard).\
        filter(models.ApplicationCard.id==channel.card_id).one()
    crate = session.query(models.Crate).\
        filter(models.Crate.id==card.crate_id).one()
    num_bits = num_bits + 1

    channelName.append(channel.name)
    channelCrate.append(str(crate.number))
    channelSlot.append(str(card.slot_number))
    channelNumber.append(str(channel.number))

   #assigning sizes to column widths for digital devices
  d_state_width = 2 * num_bits + 11
  d_name_width = 20
  d_mitigation_width = 78 - d_state_width
 
  numMitDevices = session.query(models.MitigationDevice).count()

  f.write('<table>\n')
  f.write('<title>{0} Fault States</title>\n'.format(fault.name))
  f.write('<tgroup cols=\'{0}\' align=\'left\' colsep=\'2\' rowsep=\'2\'>\n'.format(num_bits+numMitDevices+1))
  f.write('<thead>\n')
  f.write('<row>\n')
  var = 'A'
  for b in range(0, num_bits):
    f.write('  <entry>{0}</entry>\n'.format(var))
    var = chr(ord(var) + 1)
  mitDevices = writeMitigationTableHeader(f, session)
  f.write('</row>\n')
  f.write('</thead>\n')
  f.write('<tbody>\n')

  for state in fault.states:
    f.write('<row>\n')
    deviceState = session.query(models.DeviceState).\
        filter(models.DeviceState.id==state.device_state_id).one()

    bits = []
    maskBits = []
    value = deviceState.value
    mask = deviceState.mask
    for b in range(0, num_bits):
      givenMitigator = ""
      bits.append(value & 1)
      maskBits.append(mask & 1)
      value = (value >> 1)
      mask = (mask >> 1)
      if (maskBits[b] == 0):
        input_value = "-"
      else:
        input_value = bits[b]
        if (state.default == True):
          input_value = "default"

        for c in state.allowed_classes:
          beamClass = session.query(models.BeamClass).\
              filter(models.BeamClass.id==c.beam_class_id).one()
          mitigationDevice = session.query(models.MitigationDevice).\
              filter(models.MitigationDevice.id==c.mitigation_device_id).one()
          
          mitDevices[mitigationDevice.name] = beamClass.name

          givenState = deviceState.name
          givenMitigator += "[" + mitigationDevice.name + "@" + beamClass.name + "] "

        f.write('  <entry>{0}</entry>\n'.format(input_value))
    
    writeMitigationTableRows(f, deviceState.name, mitDevices)
    f.write('</row>\n')

  f.write('</tbody>\n')
  f.write('</tgroup>\n')
  f.write('</table>\n')

  # Fault Inputs
  f.write('<table>\n')
  f.write('<title>{0} Fault Inputs</title>\n'.format(fault.name))
  f.write('<tgroup cols=\'{0}\' align=\'left\' colsep=\'2\' rowsep=\'2\'>\n'.format(5))
  f.write('<thead>\n')
  f.write('<row>\n')
  f.write('  <entry>Input</entry>\n')
  f.write('  <entry>Name</entry>\n')
  f.write('  <entry>Crate</entry>\n')
  f.write('  <entry>Slot</entry>\n')
  f.write('  <entry>Channel Number</entry>\n')
  f.write('</row>\n')
  f.write('</thead>\n')
  f.write('<tbody>\n')

  var = 'A'
  for b in range(0, num_bits):
    f.write('<row>\n')
    f.write('  <entry>{0}</entry>\n'.format(var))
    f.write('  <entry>{0}</entry>\n'.format(channelName[b]))
    f.write('  <entry>{0}</entry>\n'.format(channelCrate[b]))
    f.write('  <entry>{0}</entry>\n'.format(channelSlot[b]))
    f.write('  <entry>{0}</entry>\n'.format(channelNumber[b]))
    f.write('</row>\n')
    var = chr(ord(var) + 1)

  f.write('</tbody>\n')
  f.write('</tgroup>\n')
  f.write('</table>\n')

def writeAnalogFault(f, fault, device, session):
  num_bits = 0

  channelName = []
  channelCrate = []
  channelSlot = []
  channelNumber = []
  channelMask = []

  integratorShift = 0
  if ("X" in fault.name or "I1" in fault.name):
    integratorShift = 0
  elif ("Y" in fault.name or "I2" in fault.name):
    integratorShift = 8
  elif ("TMIT" in fault.name or "I3" in fault.name):
    integratorShift = 16
  elif ("I4" in fault.name):
    integratorShift = 24
  else:
    print "ERROR: Can't recognize fault name {0}".format(fault.name)
    exit(-1)

  for state in fault.states:
    deviceState = session.query(models.DeviceState).\
        filter(models.DeviceState.id==state.device_state_id).one()
    channel = session.query(models.AnalogChannel).\
        filter(models.AnalogChannel.id==device.channel_id).one()
    card = session.query(models.ApplicationCard).\
        filter(models.ApplicationCard.id==channel.card_id).one()
    crate = session.query(models.Crate).\
        filter(models.Crate.id==card.crate_id).one()

    channelName.append(deviceState.name)
    channelCrate.append(str(crate.number))
    channelSlot.append(str(card.slot_number))
    channelNumber.append(str(channel.number))
    channelMask.append(str(hex((deviceState.mask >> integratorShift) & 0xFF)))
    
  max_bits = 8 # max number of analog thresholds
  f.write('<table>\n')
  f.write('<title>{0} Fault States</title>\n'.format(fault.name))
  f.write('<tgroup cols=\'{0}\' align=\'left\' colsep=\'2\' rowsep=\'2\'>\n'.format(max_bits+2))
  f.write('<thead>\n')
  f.write('<row>\n')
  var = 'A'
  for b in range(0, max_bits):
    f.write('  <entry>{0}</entry>\n'.format(var))
    var = chr(ord(var) + 1)
  mitDevices = writeMitigationTableHeader(f, session)
  f.write('</row>\n')
  f.write('</thead>\n')
  f.write('<tbody>\n')

  print fault.name
  print len(fault.states)
  for state in fault.states:
    f.write('<row>\n')

    num_bits = num_bits + 1
    deviceState = session.query(models.DeviceState).\
        filter(models.DeviceState.id==state.device_state_id).one()
    channel = session.query(models.AnalogChannel).\
        filter(models.AnalogChannel.id==device.channel_id).one()
    card = session.query(models.ApplicationCard).\
        filter(models.ApplicationCard.id==channel.card_id).one()
    crate = session.query(models.Crate).\
        filter(models.Crate.id==card.crate_id).one()

    v = 0x80
    actualValue = (deviceState.value >> integratorShift) & 0xFF
    for b in range(0, max_bits):
      if (v & actualValue > 0):
        f.write('  <entry>1</entry>\n')
      else:
        f.write('  <entry>-</entry>\n')
      v = (v >> 1)

      givenMitigator = ""
      for c in state.allowed_classes:
        beamClass = session.query(models.BeamClass).filter(models.BeamClass.id==c.beam_class_id).one()
        mitigationDevice = session.query(models.MitigationDevice).filter(models.MitigationDevice.id==c.mitigation_device_id).one()
        givenMitigator += "[" + mitigationDevice.name + "@" + beamClass.name + "] " #accounts for multiple mitigators
        mitDevices[mitigationDevice.name] = beamClass.name
      givenState = deviceState.name

    writeMitigationTableRows(f, fault.name, mitDevices)
    f.write('</row>\n')
  

  f.write('</tbody>\n')
  f.write('</tgroup>\n')
  f.write('</table>\n')

  # Fault Threshold Input Bits
  f.write('<table>\n')
  f.write('<title>{0} Fault Inputs (thresholds)</title>\n'.format(fault.name))
  f.write('<tgroup cols=\'{0}\' align=\'left\' colsep=\'2\' rowsep=\'2\'>\n'.format(5))
  f.write('<thead>\n')
  f.write('<row>\n')
  f.write('  <entry>Threshold</entry>\n')
  f.write('  <entry>Name</entry>\n')
  f.write('  <entry>Crate</entry>\n')
  f.write('  <entry>Slot</entry>\n')
  f.write('  <entry>Channel Number</entry>\n')
  f.write('  <entry>Threshold Mask</entry>\n')
  f.write('</row>\n')
  f.write('</thead>\n')
  f.write('<tbody>\n')

  var = 'H'
  for b in range(0, num_bits):
    f.write('<row>\n')
    f.write('  <entry>{0}</entry>\n'.format(var))
    f.write('  <entry>{0}</entry>\n'.format(channelName[b]))
    f.write('  <entry>{0}</entry>\n'.format(channelCrate[b]))
    f.write('  <entry>{0}</entry>\n'.format(channelSlot[b]))
    f.write('  <entry>{0}</entry>\n'.format(channelNumber[b]))
    f.write('  <entry>{0}</entry>\n'.format(channelMask[b]))
    f.write('</row>\n')
    var = chr(ord(var) - 1)

  f.write('</tbody>\n')
  f.write('</tgroup>\n')
  f.write('</table>\n')

def writeFault(f, fault, device, session):
  f.write('<sect3>\n')
  f.write('<title>{0} Faults</title>\n'.format(fault.name))
  f.write('<para>Fault description: {0}</para>\n'.format(fault.description))
  f.write('<para>Number of devices: {0}</para>\n'.format(len(fault.inputs)))
  
  for inp in fault.inputs:
    try:
      digitalDevice = session.query(models.DigitalDevice).\
          filter(models.DigitalDevice.id==inp.device_id).one()
      writeDigitalFault(f, fault, digitalDevice, session)
    except:
      analogDevice = session.query(models.AnalogDevice).\
          filter(models.AnalogDevice.id==inp.device_id).one()
      writeAnalogFault(f, fault, analogDevice, session)

  f.write('</sect3>\n')


def writeDeviceFaults(f, device, session):
  f.write('<sect2>\n')
  f.write('<title>{0} Faults</title>\n'.format(device.name))
  for fault_input in device.fault_outputs:
    fault = session.query(models.Fault).filter(models.Fault.id==fault_input.fault_id).one()
    writeFault(f, fault, device, session)
  f.write('</sect2>\n')

def writeDeviceInfo(f, device, session):
  #  keys = device.__dict__.keys()
  keys = ['name', 'description', 'area', 'position']

  f.write('<sect1>\n')
  f.write('<title>{0}</title>\n'.format(device.name))
  f.write('<table>\n')
  f.write('<title>{0} properties</title>\n'.format(device.name))
  f.write('<tgroup cols=\'2\' align=\'left\' colsep=\'1\' rowsep=\'1\'>\n')
  f.write('<thead>\n')
  f.write('<row>\n')
  f.write('  <entry>Property</entry>\n')
  f.write('  <entry>Value</entry>\n')
  f.write('</row>\n')
  f.write('</thead>\n')
  f.write('<tbody>\n')

  for k in keys:
    if not k.startswith('_'):
      f.write('<row>\n')
      f.write('  <entry>{0}</entry>\n'.format(k))
      f.write('  <entry>{0}</entry>\n'.format(getattr(device, k)))
      f.write('</row>\n')

  f.write('</tbody>\n')
  f.write('</tgroup>\n')
  f.write('</table>\n')

  writeDeviceFaults(f, device, session)

  f.write('</sect1>\n')

def exportDocBook(session, fileName):
  f = open(fileName, "w")

  writeHeader(f)

  f.write('<chapter><title>MPS Devices</title>\n')
  for device in session.query(models.Device).all():
    writeDeviceInfo(f, device, session)
  f.write('</chapter>\n')
  f.write('</book>\n')
  f.close()

parser = argparse.ArgumentParser(description='Print database inputs/logic')
parser.add_argument('database', metavar='db', type=file, nargs=1,
                    help='database file name (e.g. mps_gun.db)')

args = parser.parse_args()

mps = MPSConfig(args.database[0].name)
session = mps.session

exportDocBook(session, "./test.doc")

session.close()
