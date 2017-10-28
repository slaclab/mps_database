#!/usr/bin/env python

from mps_config import MPSConfig, models
import sys
import argparse

def printDb(session):
  screen_width = 100 #sets uniform screen width

  for device in session.query(models.Device).all():
    print ""
    print (screen_width+2) * "*"
    print "| Device: " + device.name
    print (screen_width+2) * "*"
    print ""
    print "+" + (screen_width * "=") + "+"
    print "| Faults"
    print "+" + (screen_width * "=") + "+"
    for fault_input in device.fault_outputs:
      fault = session.query(models.Fault).filter(models.Fault.id==fault_input.fault_id).one()
      print ""
      print "+" + (screen_width * "-") + "+"
      print "| [" + str(fault.id) + "] Fault:",
      print ("{:{key_pad}} |".format(fault.name, key_pad = screen_width - len(str(fault.id)) - len("| [] Fault: ")))

      channelNames = []
      num_bits = 0
      for inp in fault.inputs:
        #check for either analog or digital
        analog = False
        try:
          digitalDevice = session.query(models.DigitalDevice).filter(models.DigitalDevice.id==inp.device_id).one()
        except:
          analogDevice = session.query(models.AnalogDevice).filter(models.AnalogDevice.id==inp.device_id).one()
          analog = True
        if (analog == False): #digital devices
          for ddi in digitalDevice.inputs:
            channel = session.query(models.DigitalChannel).filter(models.DigitalChannel.id==ddi.channel_id).one()
            card = session.query(models.ApplicationCard).filter(models.ApplicationCard.id==channel.card_id).one()
            crate = session.query(models.Crate).filter(models.Crate.id==card.crate_id).one()
            num_bits = num_bits + 1
            channelNames.append(channel.name + " - " + digitalDevice.description + " [crate: " + str(crate.number) + ", slot: " + str(card.slot_number)+ ", channel: " + str(channel.number)+ "]")
        else: #analog devices
          for state in fault.states:
            num_bits = num_bits + 1
            deviceState = session.query(models.DeviceState).filter(models.DeviceState.id==state.device_state_id).one()
            channel = session.query(models.AnalogChannel).filter(models.AnalogChannel.id==analogDevice.channel_id).one()
            card = session.query(models.ApplicationCard).filter(models.ApplicationCard.id==channel.card_id).one()
            crate = session.query(models.Crate).filter(models.Crate.id==card.crate_id).one()
            channelNames.append(deviceState.name + " [crate: " + str(crate.number) + ", slot: " + str(card.slot_number)+ ", channel: " + str(channel.number)+ "]")

      if (analog == False):
        #assigning sizes to column widths for digital devices
        d_state_width = 2 * num_bits + 11
        d_name_width = 20
        d_mitigation_width = 78 - d_state_width

        #printing out head of fault table
        print "+" + (d_state_width  * "-") + "+" + (d_name_width * "-") + "+" + (d_mitigation_width * "-") + "+"
        print "| ",
        var_string = ""
        var = 'A'
        for b in range(0,num_bits):
          var_string += var
          var_string += " "
          var = chr(ord(var) + 1)
        name_string = "Name"
        mitigation_string = "Mitigation"
        #pad values allows for ability to set boundaries in which strings must fit into
        print "{:{key_pad}}  |".format(var_string, key_pad = d_state_width - 4),
        print "{:{key_pad}}  |".format(name_string, key_pad = d_name_width - 3),
        print "{:{key_pad}}  |".format(mitigation_string, key_pad = d_mitigation_width - 3)
        print "+" + (d_state_width  * "-") + "+" + (d_name_width * "-") + "+" + (d_mitigation_width * "-") + "+"

        #printing out fault contents
        for state in fault.states:
          deviceState = session.query(models.DeviceState).filter(models.DeviceState.id==state.device_state_id).one()
          print "| ",
          bits = []
          maskBits = []
          value = deviceState.value
          mask = deviceState.mask
          state_tuple = []
          for b in range(0,num_bits):
            bits.append(value & 1)
            maskBits.append(mask & 1)
            value = (value >> 1)
            mask = (mask >> 1)
            if (maskBits[b] == 0):
              state_tuple += "- "
            else:
              state_tuple += bits[b],
              state_tuple += " ",
          if (state.default == True):
            state_tuple += " default"
          state_string = ""
          for x in range(0, len(state_tuple)):
            state_string += str(state_tuple[x])
          for c in state.allowed_classes:
            beamClass = session.query(models.BeamClass).filter(models.BeamClass.id==c.beam_class_id).one()
            mitigationDevice = session.query(models.MitigationDevice).filter(models.MitigationDevice.id==c.mitigation_device_id).one()
          givenState = deviceState.name
          givenMitigator = "[" + mitigationDevice.name + "@" + beamClass.name + "] "
          print ("{:{state_pad}}".format(state_string, state_pad = d_state_width-3)),
          print ("| {:{key_pad}} | {:{value_pad}} |".format(givenState, givenMitigator,
                                                            key_pad = d_name_width-2,value_pad = d_mitigation_width-2))
        print "+" + (d_state_width  * "-") + "+" + (d_name_width * "-") + "+" + (d_mitigation_width * "-") + "+"

        #input values for faults
        print "\nInputs:"
        var = 'A'
        for b in range(0, num_bits):
          print " " + var + ": " + channelNames[b]
          var = chr(ord(var) + 1)

      else: #device is analog
        #assigning sizes to column widths for analog devices
        a_state_width = 20
        a_name_width = 12
        a_mitigation_width = 86 - a_state_width

        #printing out head of fault table
        print "+" + (a_state_width  * "-") + "+" + (a_name_width * "-") + "+" + (a_mitigation_width * "-") + "+"
        print "| ",
        var = 'A'
        for b in range(0,8):
          print var,
          var = chr(ord(var) + 1)
        mitigation_string = "Mitigation"
        print "  | Name       |",
        print "{:{key_pad}}  |".format(mitigation_string, key_pad = a_mitigation_width - 3)
        print "+" + (a_state_width  * "-") + "+" + (a_name_width * "-") + "+" + (a_mitigation_width * "-") + "+"

        #print out contents of fault table
        for state in fault.states:
          print "| ",
          deviceState = session.query(models.DeviceState).filter(models.DeviceState.id==state.device_state_id).one()
          bits = []
          maskBits = []
          anti_bits = []
          anti_mask = []
          if ("_X" in fault.name):
            value = deviceState.value
            mask = deviceState.mask
          if ("_Y" in fault.name):
            value = (deviceState.value >> 8)
            mask = (deviceState.mask >> 8)
          if ("_T" in fault.name):
            value = (deviceState.value >> 16)
            mask = (deviceState.mask >> 16)
          for b in range(0, 8 - num_bits):
            maskBits.append(0)
          for b in range(0, 8):
            anti_bits.append(value & 1)
            anti_mask.append(mask & 1)
            value = (value >> 1)
            mask = (mask >> 1)
          for b in range(0, 8):
            bits.append(anti_bits[num_bits-b-1])
            maskBits.append(anti_mask[num_bits-b-1])
          for b in range(0, 8):
            if (maskBits[b] == 1):
              print '1',
            else:
              print '-',
          if (state.default == True):
            print "default",
          else:
            print " ",
          givenMitigator = ""
          for c in state.allowed_classes:
            beamClass = session.query(models.BeamClass).filter(models.BeamClass.id==c.beam_class_id).one()
            mitigationDevice = session.query(models.MitigationDevice).filter(models.MitigationDevice.id==c.mitigation_device_id).one()
            givenMitigator += "[" + mitigationDevice.name + "@" + beamClass.name + "] " #accounts for multiple mitigators
          givenState = deviceState.name
          print ("| {:{key_pad}} | {:{value_pad}} |".format(givenState, givenMitigator,
                                                            key_pad = 10, value_pad = a_mitigation_width-2))
        print "+" + (a_state_width  * "-") + "+" + (a_name_width * "-") + "+" + (a_mitigation_width * "-") + "+"


        print "\nThresholds:"
        var = 'A'
        for b in range(0, num_bits):
          print " " + var + ": " + channelNames[b]
          var = chr(ord(var) + 1)
  

  print ""
  print "+" + (screen_width * "=") + "+"
  print "| Ignore Logic"
  print "+" + (screen_width * "=") + "+"
  for condition in session.query(models.Condition).all():
    print ""
    print "+" + (screen_width * "-") + "+"
    condition_string = "| Condition: " + condition.name + " value: " + "0x%0.4X" % condition.value
    print ("{:{condition_pad}} |".format(condition_string, condition_pad = screen_width))
    print "+" + (screen_width * "-") + "+"
    for inp in condition.condition_inputs:
      faultState = session.query(models.FaultState).filter(models.FaultState.id==inp.fault_state_id).one()
      deviceState = session.query(models.DeviceState).filter(models.DeviceState.id==faultState.device_state_id).one()
      input_string = "| bit " + str(inp.bit_position) + ": " + inp.fault_state.fault.name + ", value: " + str(deviceState.value)
      print ("{:{input_pad}} |".format(input_string, input_pad = screen_width))
    print "+" + (screen_width * "-") + "+"

    ignfault_string = "Ignored Faults: "
    print ("| {:{ignored_pad}} |".format(ignfault_string, ignored_pad = screen_width-2))
    print "+" + (screen_width * "-") + "+"
    for ignore_fault in condition.ignore_conditions:
      if (hasattr(ignore_fault.fault_state, 'fault_id')):
        ignfaultst_string = "[" + str(ignore_fault.fault_state.fault_id) + "]\t" + ignore_fault.fault_state.fault.name + " (digital)"
        print ("| {:{ignst_pad}} |".format(ignfaultst_string, ignst_pad = screen_width-4))
      else:
        print "| " + "[" + str(ignore_fault.fault_state.threshold_fault_id) + "]\t",
        print ignore_fault.fault_state.threshold_fault.name + " (threshold)"
    print "+" + (screen_width * "-") + "+"

#=== MAIN ===================================================================================================================================

parser = argparse.ArgumentParser(description='Print database inputs/logic')
parser.add_argument('database', metavar='db', type=file, nargs=1,
                    help='database file name (e.g. mps_gun.db)')

args = parser.parse_args()

mps = MPSConfig(args.database[0].name)
session = mps.session

printDb(session)

session.close()
