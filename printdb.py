from mps_config import MPSConfig, models
import sys

#mps = MPSConfig('mps_sxrss.db')

if (len(sys.argv) == 2):
  file_name = sys.argv[1]
else:
  file_name = 'mps_gun_config.db'

mps = MPSConfig(file_name)
session = mps.session
print "+==================================================================+"
print "| Digital Faults"
print "+==================================================================+"
for fault in session.query(models.Fault).all():
  print ""
  print "+------------------------------------------------------------------+"
  print "| [" + str(fault.id) + "] Fault: " + fault.name
  channelNames = []
  num_bits = 0
  for inp in fault.inputs:
    digitalDevice = session.query(models.DigitalDevice).filter(models.DigitalDevice.id==inp.id).one()
    channels = []
    for ddi in digitalDevice.inputs:
      channel = session.query(models.DigitalChannel).filter(models.DigitalChannel.id==ddi.channel_id).one()
      card = session.query(models.ApplicationCard).filter(models.ApplicationCard.id==channel.card_id).one()
      crate = session.query(models.Crate).filter(models.Crate.id==card.crate_id).one()
      num_bits = num_bits + 1
      channelNames.append(channel.name + " - " + digitalDevice.description + " [crate: " + str(crate.number) +
                          ", slot: " + str(card.slot_number)+ ", channel: " + str(channel.number)+ "]")
      

  print "+---------------+-----------------------+--------------------------+"
  print "| ",
  var = 'A'
  for b in range(0,num_bits):
    print var,
    var = chr(ord(var) + 1)
  print "State\t| Name\t\t\t| Mitigation"
  print "+---------------+-----------------------+--------------------------+"

  for state in fault.states:
    print "| ",
    deviceState = session.query(models.DeviceState).filter(models.DeviceState.id==state.device_state_id).one()
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
    print "0x%0.4X" % deviceState.value, 
    print "\t| " + deviceState.name + "\t|",
    for c in state.allowed_classes:
      beamClass = session.query(models.BeamClass).filter(models.BeamClass.id==c.beam_class_id).one()
      mitigationDevice = session.query(models.MitigationDevice).filter(models.MitigationDevice.id==c.mitigation_device_id).one()
      print "[" + mitigationDevice.name + "@" + beamClass.name + "] ",
    print ""
  print "+---------------+-----------------------+--------------------------+"

  print "\nInputs:"
  var = 'A'
  for b in range(0,num_bits):
    print " " + var + ": " + channelNames[b]
    var = chr(ord(var) + 1)

print ""

print "+==================================================================+"
print "| Analog Faults"
print "+==================================================================+"
for fault in session.query(models.ThresholdFault).all():
  print ""
  analogDevice = session.query(models.AnalogDevice).filter(models.AnalogDevice.id==fault.analog_device_id).one()
  thresholdValue = session.query(models.ThresholdValue).filter(models.ThresholdValue.id==fault.threshold_value_id).one()
#  print fault.name + " " + analogDevice.name + ": " + analogDevice.description + " " + str(thresholdValue.value),
  print "+------------------------------------------------------------------+"
  print "| [" + str(fault.id) + "] Fault: " + fault.name
  print "| Analog Input: " + analogDevice.name + " - " + analogDevice.description
  print "+-------+---------------+---------------+--------------------------+"
  print "| Value\t| Threshold\t| Comparison\t| Mitigation"
  print "+-------+---------------+---------------+--------------------------+"

  if (fault.greater_than):
    comp = analogDevice.name + " >= " + str(thresholdValue.threshold)
  else:
    comp = analogDevice.name + " < " + str(thresholdValue.threshold)
    
  state = session.query(models.ThresholdFaultState).filter(models.ThresholdFaultState.threshold_fault_id==fault.id).one()
  for c in state.allowed_classes:
    beamClass = session.query(models.BeamClass).filter(models.BeamClass.id==c.beam_class_id).one()
    mitigationDevice = session.query(models.MitigationDevice).filter(models.MitigationDevice.id==c.mitigation_device_id).one()
    print "| " + str(thresholdValue.value) + "\t| " + str(thresholdValue.threshold) + "\t\t| " + comp + "\t| ",
    print "[" + mitigationDevice.name + "@" + beamClass.name + "] "
    print "+-------+---------------+---------------+--------------------------+"

  print ""

print "+==================================================================+"
print "| Ignore Logic"
print "+==================================================================+"
for condition in session.query(models.Condition).all():
  print ""
  print "+------------------------------------------------------------------+"
  print "| Condition: " + condition.name + " value: ",
  print "0x%0.4X" % condition.value
  print "+------------------------------------------------------------------+"
  for inp in condition.condition_inputs:
    print "| bit " + str(inp.bit_position) + ": " + inp.fault_state.fault.name
  print "+------------------------------------------------------------------+"

  print "| Ignored Faults:"
  print "+------------------------------------------------------------------+"
  for ignore_fault in condition.ignore_conditions:
    if (hasattr(ignore_fault.fault_state, 'fault_id')):
      print "| " + "[" + str(ignore_fault.fault_state.fault_id) + "]\t" + ignore_fault.fault_state.fault.name + " (digital)"
    else:
      print "| " + "[" + str(ignore_fault.fault_state.threshold_fault_id) + "]\t",
      print ignore_fault.fault_state.threshold_fault.name + " (threshold)"
  print "+------------------------------------------------------------------+"
