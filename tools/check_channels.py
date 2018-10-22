#!/usr/bin/env python

from mps_config import MPSConfig, models
from mps_names import MpsName
from sqlalchemy import func
import sys
import argparse
import time 
import os

def checkChannels(session):
  checkDigitalChannels(session)
  checkAnalogChannels(session)

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
        otherChannel=session.query(models.DigitalChannel).filter(models.DigitalChannel.id==card[c.card_id][c.number]).one()
        otherDeviceInput=session.query(models.DeviceInput).filter(models.DeviceInput.channel_id==card[c.card_id][c.number]).one()
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



#=== MAIN ==================================================================================

parser = argparse.ArgumentParser(description='Check for duplicate channel assignments')
parser.add_argument('database', metavar='db', type=file, nargs=1, 
                    help='database file name (e.g. mps_gun.db)')

args = parser.parse_args()

mps = MPSConfig(args.database[0].name)
session = mps.session

checkChannels(session)

session.close()

