#!/usr/bin/env python

from mps_config import MPSConfig, models, runtime
from mps_names import MpsName
from sqlalchemy import func
import sys
import argparse
import time 
import os

def checkChannels(session):
  checkDigitalChannels(session)
  checkAnalogChannels(session)
  count(session)

def countDeviceTypes(t, session):
  devices=session.query(models.Device).\
      filter(models.Device.device_type_id==t.id).all()
#  if (len(devices) > 0):
  print(' {0}: {1}'.format(t.name, len(devices)))

  return len(devices)

def count(session):
  devices=session.query(models.Device).all()
  print 'Total devices: {0}'.format(len(devices))
  types=session.query(models.DeviceType).all()
  typeWithoutDevices = False
  for t in types:
    l = countDeviceTypes(t, session)
    if (l == 0):
      typeWithoutDevices = True

  if (typeWithoutDevices):
    print 'WARN: Database has DeviceTypes with not Devices defined'

def checkAnalogChannels(session):
  channels=session.query(models.AnalogChannel).all()

  card={}
  error=False
  for c in channels:
    analogDevice=session.query(models.AnalogDevice).filter(models.AnalogDevice.channel_id==c.id).one()

    # Check if channel number is valid (i.e. does not exceed number of supported channels)
    if c.number > analogDevice.card.type.analog_channel_count-1:
      print 'ERROR: invalid channel number assigned to device {0} in card id {1}, channel {2}'.\
          format(analogDevice.name, analogDevice.card_id, c.number)
      print '       [crate {0}, slot {1}, num channels {2}]'.\
          format(analogDevice.card.crate.get_name(), analogDevice.card.slot_number,
                 analogDevice.card.type.analog_channel_count)

    if not c.card_id in card.keys():
      card[c.card_id]={}
      card[c.card_id][c.number]=c.id
    else:
      if c.number in card[c.card_id].keys():
        otherChannel=session.query(models.AnalogChannel).filter(models.AnalogChannel.id==card[c.card_id][c.number]).one()
        otherAnalogDevice=session.query(models.AnalogDevice).filter(models.AnalogDevice.channel_id==card[c.card_id][c.number]).one()
        print 'ERROR: channel {0} of card id {1} (crate {2}, slot {3}) assigned to both channels {4} ({5}) and {6} ({7})'.\
            format(c.number, c.card_id, c.card.crate.get_name(), c.card.slot_number,
                   otherChannel.name, otherAnalogDevice.name,
                   c.name, analogDevice.name)
        error=True
      else:
        card[c.card_id][c.number]=c.id

  if error:
    print 'Please check database for duplicate analog channel assignments!'
  else:
    print 'Database OK for analog channels, no duplicate assignmets found.'

def checkDigitalChannels(session):
  channels=session.query(models.DigitalChannel).all()

  card={}
  error=False
  softError=False
  for c in channels:
    deviceInput=session.query(models.DeviceInput).filter(models.DeviceInput.channel_id==c.id).one()

    # Check if channel number is valid (i.e. does not exceed number of supported channels)
    if c.number > deviceInput.channel.card.type.digital_channel_count-1:
      print 'ERROR: invalid channel number assigned to device {0} in card id {1}, channel {2}'.\
          format(deviceInput.channel.name, deviceInput.channel.card_id, c.number)
      print '       [crate {0}, slot {1}, num channels {2}]'.\
          format(deviceInput.channel.card.crate.get_name(), deviceInput.channel.card.slot_number,
                 deviceInput.channel.card.type.digital_channel_count)

    if not c.card_id in card.keys():
      card[c.card_id]={}
      card[c.card_id][c.number]=c.id
    else:
      if c.number in card[c.card_id].keys():
        otherChannel=session.query(models.DigitalChannel).\
            filter(models.DigitalChannel.id==card[c.card_id][c.number]).one()
        otherDeviceInput=session.query(models.DeviceInput).\
            filter(models.DeviceInput.channel_id==card[c.card_id][c.number]).one()
        print 'ERROR: channel {0} of card id {1} (crate {2}, slot {3}) assigned to both channels {4} ({5}) and {6} ({7})'.\
            format(c.number, c.card_id, c.card.crate.get_name(), c.card.slot_number,
                   otherChannel.name, otherDeviceInput.digital_device.name,
                   c.name, deviceInput.digital_device.name)
        error=True
      else:
        card[c.card_id][c.number]=c.id

    # If this is a 'soft' digital channel verify if the contents of
    # num_inputs/monitored_pvs is correct
    if c.num_inputs > 0:
      if (c.num_inputs != len(c.monitored_pvs.split(';'))):
        print 'ERROR: channel {0} of card id {1} number of PV inputs ({2}) does not match with the number of PVs listed ({3}).'.\
            format(c.number, c.card_id, c.num_inputs, len(c.monitored_pvs.split(';')))
        print '       PVs should be separated by semi-colons. This are the PVs found:'
        for s in c.monitored_pvs.split(';'):
          print '       - \'{0}\''.format(s.strip())
        error=True
        softError=True

  if error:
    if softError:
      print 'Detected bad soft channel specifications, please check!'
    print 'Please check database for duplicate digital channel assignments!'
  else:
    print 'Database OK for digital channels, no duplicate assignments found'

def checkLinkNodes(session):
  link_nodes = session.query(models.LinkNode).all()
  for ln in link_nodes:
    for ln2 in link_nodes:
      if (ln.get_name() == ln2.get_name() and
          ln.id != ln2.id):
        print 'ERROR: duplicate LinkNode name: {0}, found for LN ID {1} and {2}'.\
            format(ln.get_name(), ln.id, ln2.id)

def checkRuntime(session, rt_session):
  devices = session.query(models.Device).all()
  rt_devices = session.query(models.Device).all()

  if (len(devices) != len(rt_devices)):
    print 'ERROR: Number of devices in static database ({0}) different from runtime database ({1})'.\
        format(len(devices),len(rt_devices))

  missing={}
  for d in devices:
    try:
      rt_d = rt_session.query(runtime.Device).filter(runtime.Device.mpsdb_id==d.id).one()
      if (rt_d.mpsdb_name != d.name):
        print 'ERROR: Found device with same id, but different names in static/runtime databases'
        print '       id={0}, static name={1}, runtime name={2}'.format(d.id, d.name, rt_d.mpsdb_name)

      # check if there are threshold table entries
      # *not implemented*

    except Exception as e:
      print e
      missing[d.id]=d.name

  if (len(missing)>0):
    print 'ERROR: There are devices in config database not included in the runtime database, please check'
  else:
    print 'Runtime database OK'
#    if (verbose):
#      for k,i in missing.iteritems():
#        print '  id={0} name={1}'.format(k, i)


#=== MAIN ==================================================================================

parser = argparse.ArgumentParser(description='Check for duplicate channel assignments')
parser.add_argument('database', metavar='db', type=file, nargs=1, 
                    help='database file name (e.g. mps_gun.db)')

args = parser.parse_args()

mps = MPSConfig(args.database[0].name, args.database[0].name.split('.')[0]+'_runtime.db')
session = mps.session
rt_session = mps.runtime_session

checkChannels(session)
checkLinkNodes(session)
checkRuntime(session, rt_session)

session.close()

