#!/usr/bin/env python
from mps_database.mps_config import MPSConfig, models, runtime
from sqlalchemy import MetaData
from mps_database.tools.mps_names import MpsName
import argparse
import time
import yaml
import os
import sys

class AddDigitalDevice:

  def __init__(self, session,conf,verbose):
    self.verbose = verbose
    self.session = session
    self.conf = conf
    self.mps_names = MpsName(self.session)

  #def __del__(self):
  #  self.session.commit()

  def add_digital_device(self,device_info):
    if self.verbose:
      print("Adding digital device {0}".format(device_info['device']))
    device_type = self.conf.find_device_type(self.session,device_info['type'])
    device_name = self.mps_names.makeDeviceName(device_info['device'],device_type.name,device_info['channel'])
    application_card = self.conf.find_app_card(self.session,device_info['appid'])
    device = self.add_device(device_name,device_info['device'].split(":")[2],device_info['z'],
                             device_info['description'],device_type,application_card,device_info['device'].split(":")[1],
                             device_info['evaluation'])
    channel = self.add_channel(device_info,application_card)
    if channel is None:
      print("INFO: Device Input not created for {0}".format(device_info['device']))
    if channel is not None:
      device_input = self.add_input(device_info,device,channel)
    self.session.commit()


  def add_device(self,name,position,z_location,description,device_type,card,area,evaluation):
    found_device = self.session.query(models.DigitalDevice).filter(models.DigitalDevice.name == name).all()
    if len(found_device) > 0:
      return found_device[0]
    else:
      device = models.DigitalDevice(name=name,
                                    position=position,
                                    z_location=z_location,
                                    description=description,
                                    device_type=device_type,
                                    card=card,
                                    area=area,
                                    evaluation=evaluation)
      self.session.add(device)
      return device

  def add_channel(self,device_info,card):
    used_channels = []
    for ch in card.digital_channels:
      used_channels.append(ch.number)
    if int(device_info['channel']) in used_channels:
      print("ERROR: Channel {0} already used in app {1}".format(device_info['channel'],card.number))
      return
    if int(device_info['channel']) > card.type.digital_channel_count:
      print("ERROR: Invalid channel number {0}".format(device_info['channel']))
      return
    alarm_state = 0
    if int(device_info['evaluation']) > 0:
      alarm_state = 1
    if int(device_info['channel']) > 31:
      digital_channel = models.DigitalChannel(number=int(device_info['channel']),
                                              name=device_info['device'],
                                              z_name=device_info['z_name'],
                                              o_name=device_info['o_name'],
                                              alarm_state=alarm_state,
                                              card=card,
                                              num_inputs=1,
                                              monitored_pvs=device_info['device'],
                                              description=device_info['description'])
    else:
      digital_channel = models.DigitalChannel(number=int(device_info['channel']),
                                              name=device_info['device'],
                                              z_name=device_info['z_name'],
                                              o_name=device_info['o_name'],
                                              alarm_state=alarm_state,
                                              card=card,
                                              description=device_info['description'])
    self.session.add(digital_channel)
    return digital_channel

  def add_input(self,device_info,device,channel):
    alarm_state = 0
    if int(device_info['evaluation']) > 0:
      alarm_state = 1
    device_input = models.DeviceInput(channel=channel,
                                      bit_position=device_info['bit_position'],
                                      digital_device = device,
                                      fault_value = alarm_state,
                                      auto_reset=int(device_info['auto_reset']))
    self.session.add(device_input)
    return device_input
    
    


        



