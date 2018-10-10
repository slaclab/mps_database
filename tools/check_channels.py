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
  for c in channels:
    deviceInput=session.query(models.DeviceInput).filter(models.DeviceInput.channel_id==c.id).one()

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

  if error:
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

