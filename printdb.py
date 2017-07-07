#!/usr/bin/env python

from mps_config import MPSConfig, models
import sys
import argparse


def printDb(session):
  screen_width = 90 #sets uniform screen width
  print "+" + (screen_width * "=") + "+"
  print "| Faults"
  print "+" + (screen_width * "=") + "+"
  for fault in session.query(models.Fault).all():
    print ""
    print "+" + (screen_width * "-") + "+"
    print "| [" + str(fault.id) + "] Fault: " + fault.name
    channelNames = []
    num_bits = 0
    for inp in fault.inputs:
      analog = False
      try:
        digitalDevice = session.query(models.DigitalDevice).filter(models.DigitalDevice.id==inp.device_id).one()
      except:
        analogDevice = session.query(models.AnalogDevice).filter(models.AnalogDevice.id==inp.device_id).one()
        analog = True

      if (analog == False):
        for ddi in digitalDevice.inputs:
          channel = session.query(models.DigitalChannel).filter(models.DigitalChannel.id==ddi.channel_id).one()
          card = session.query(models.ApplicationCard).filter(models.ApplicationCard.id==channel.card_id).one()
          crate = session.query(models.Crate).filter(models.Crate.id==card.crate_id).one()
          num_bits = num_bits + 1
          channelNames.append(channel.name + " - " + digitalDevice.description + " [crate: " + str(crate.number) +
                              ", slot: " + str(card.slot_number)+ ", channel: " + str(channel.number)+ "]")
      else:
        for state in fault.states:
          num_bits = num_bits + 1
          deviceState = session.query(models.DeviceState).filter(models.DeviceState.id==state.device_state_id).one()
          channel = session.query(models.AnalogChannel).filter(models.AnalogChannel.id==analogDevice.channel_id).one()
          card = session.query(models.ApplicationCard).filter(models.ApplicationCard.id==channel.card_id).one()
          crate = session.query(models.Crate).filter(models.Crate.id==card.crate_id).one()
          channelNames.append(deviceState.name + " [crate: " + str(crate.number) +
                              ", slot: " + str(card.slot_number)+ ", channel: " + str(channel.number)+ "]")

    #assigning sizes to column widths
    state_width = 18
    name_width = 18
    mitigation_width = 52

    print "+" + (state_width  * "-") + "+" + (name_width * "-") + "+" + (mitigation_width * "-") + "+"
    print "| ",
    var = 'A'
    for b in range(0,num_bits):
      print var,
      var = chr(ord(var) + 1)
    if (num_bits < 4):
      print "State\t   | Name\t      | Mitigation"
    if (num_bits == 4):
      print "State   | Name\t      | Mitigation"
    print "+" + (state_width  * "-") + "+" + (name_width * "-") + "+" + (mitigation_width * "-") + "+"

    if (analog == False):
      for state in fault.states:
        deviceState = session.query(models.DeviceState).filter(models.DeviceState.id==state.device_state_id).one()
        print "| ",
        bits = []
        maskBits = []
        value = deviceState.value
	mask = deviceState.mask
        for b in range(0,num_bits):
          bits.append(value & 1)
          maskBits.append(mask & 1)
          value = (value >> 1)
          mask = (mask >> 1)
          if (maskBits[b] == 0):
            print '-',
          else:
            print bits[b],
        if (state.default == True):
          print "default",
        else:
          print "0x%0.4X" % deviceState.value,
        #accounting for when state columns have either A or A and B to account for
        if (num_bits == 1):
          print "      ",
        if (num_bits == 2):
          print "    ",
        for c in state.allowed_classes:
          beamClass = session.query(models.BeamClass).filter(models.BeamClass.id==c.beam_class_id).one()
          mitigationDevice = session.query(models.MitigationDevice).filter(models.MitigationDevice.id==c.mitigation_device_id).one()
	givenState = deviceState.name
        givenMitigator = "[" + mitigationDevice.name + "@" + beamClass.name + "] "
        #sets boundaries in which states and mitigation labels must fit into
        print ("| {:{key_pad}} | {:{value_pad}} |".format(givenState, givenMitigator,
                                                          key_pad = 16,value_pad = 50))
    else:
      for state in fault.states:
        print "| ",
        deviceState = session.query(models.DeviceState).filter(models.DeviceState.id==state.device_state_id).one()
        bits = []
        maskBits = []
        anti_bits = []
        anti_mask = []
        value = deviceState.value
        mask = deviceState.mask
        for b in range(0,num_bits):
          anti_bits.append(value & 1)
          anti_mask.append(mask & 1)
          value = (value >> 1)
          mask = (mask >> 1)
        for b in range(0, num_bits):
          bits.append(anti_bits[num_bits-b-1])
	maskBits.append(anti_mask[num_bits-b-1])
        for b in range(0,num_bits):
          if (maskBits[b] == 1):
            print '-',
          else:
            print bits[b],
        if (state.default == True):
          print "default",
        else:
          print "0x%0.4X " % deviceState.value,
        givenMitigator = ""
        for c in state.allowed_classes:
          beamClass = session.query(models.BeamClass).filter(models.BeamClass.id==c.beam_class_id).one()
          mitigationDevice = session.query(models.MitigationDevice).filter(models.MitigationDevice.id==c.mitigation_device_id).one()
          givenMitigator += "[" + mitigationDevice.name + "@" + beamClass.name + "] " #accounts for multiple mitigators
        givenState = deviceState.name
        print ("| {:{key_pad}} | {:{value_pad}} |".format(givenState, givenMitigator,
                                                          key_pad = 16, value_pad = 50)),
        print ""
    print "+" + (state_width  * "-") + "+" + (name_width * "-") + "+" + (mitigation_width * "-") + "+"
    if (analog == False):
      print "\nInputs:"
      var = 'A'
 for b in range(0,num_bits):
        print " " + var + ": " + channelNames[b]
        var = chr(ord(var) + 1)
    else:
      print "\nThresholds:"
      var = 'A'
      for b in range(0,num_bits):
        print " " + var + ": " + channelNames[b]
        var = chr(ord(var) + 1)

  print ""
  print "+" + (screen_width * "=") + "+"
  print "| Ignore Logic"
  print "+" + (screen_width * "=") + "+"
  for condition in session.query(models.Condition).all():
    print ""
    print "+" + (screen_width * "-") + "+"
    print "| Condition: " + condition.name + " value: ",
    print "0x%0.4X" % condition.value
    print "+" + (screen_width * "-") + "+"
    for inp in condition.condition_inputs:
      faultState = session.query(models.FaultState).filter(models.FaultState.id==inp.fault_state_id).one()
      deviceState = session.query(models.DeviceState).filter(models.DeviceState.id==faultState.device_state_id).one()
      print "| bit " + str(inp.bit_position) + ": " + inp.fault_state.fault.name + ", value: " + str(deviceState.value)
    print "+" + (screen_width * "-") + "+"

    print "| Ignored Faults:"
    print "+" + (screen_width * "-") + "+"
    for ignore_fault in condition.ignore_conditions:
      if (hasattr(ignore_fault.fault_state, 'fault_id')):
        print "| " + "[" + str(ignore_fault.fault_state.fault_id) + "]\t" + ignore_fault.fault_state.fault.name + " (digital)"
      else:
        print "| " + "[" + str(ignore_fault.fault_state.threshold_fault_id) + "]\t",
        print ignore_fault.fault_state.threshold_fault.name + " (threshold)"
    print "+" + (screen_width * "-") + "+"


#=== MAIN ==================================================================================

parser = argparse.ArgumentParser(description='Print database inputs/logic')
parser.add_argument('database', metavar='db', type=file, nargs=1,
                    help='database file name (e.g. mps_gun.db)')

args = parser.parse_args()

mps = MPSConfig(args.database[0].name)
session = mps.session

printDb(session)

session.close()
