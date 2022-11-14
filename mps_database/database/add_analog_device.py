#!/usr/bin/env python
from mps_database.mps_config import MPSConfig, models, runtime
from sqlalchemy import MetaData
from mps_database.tools.mps_names import MpsName
import argparse
import time
import yaml
import os
import sys

class AddAnalogDevice:

  def __init__(self, session,conf,verbose):
    self.session = session
    self.verbose = verbose
    self.conf = conf
    self.mps_names = MpsName(self.session)

  def __del__(self):
    self.session.commit()

  def add_analog_device(self,device_info):
    if self.verbose:
      print("Adding analog device {0}".format(device_info['device']))
    device_type = self.conf.find_device_type(self.session,device_info['type'],True)
    device_name = self.mps_names.makeDeviceName(device_info['device'],device_type.name,device_info['channel'])
    application_card = self.conf.find_app_card(self.session,device_info['appid'])
    channel = self.add_channel(device_info,application_card)
    slope = 1
    offset = 0
    cable = "N/A"
    fields = device_info.keys()
    if "slope" in fields:
      if device_info['slope'] != '':
        slope = device_info['slope']
    if "offset" in fields:
      if device_info['offset'] != '':
        offset = device_info['offset']
    if "cable" in fields:
      if device_info['cable'] != '':
        cable = device_info['cable']
    if channel is not None:
      device = models.AnalogDevice(name=device_name,
                                   device_type=device_type,
                                   channel=channel,
                                   card=application_card,
                                   position=device_info['device'].split(":")[2],
                                   area=device_info['device'].split(":")[1],
                                   z_location=device_info['z'],
                                   description=device_info['description'],
                                   evaluation=1,
                                   cable_number=cable,
                                   slope=slope,
                                   offset=offset)
    else:
      print("INFO: Device {0} not added because of channel error".format(device_name))
    self.session.commit()

  def add_channel(self,device_info,card):
    used_channels = []
    for ch in card.analog_channels:
      used_channels.append(ch.number)
    if int(device_info['channel']) in used_channels:
      print("ERROR: Channel {0} already used in app {1}".format(device_info['channel'],card.number))
      return
    if int(device_info['channel']) > card.type.analog_channel_count:
      print("ERROR: Invalid channel number {0}".format(device_info['channel']))
      return
    analog_channel = models.AnalogChannel(name=device_info['device'],
                                          number=int(device_info['channel']), card=card)
    self.session.add(analog_channel)
    return analog_channel
