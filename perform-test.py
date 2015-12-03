from mps_config import MPSConfig, models

#Use the database to make an empty machine state data structure.
#This code is pretty inefficient.
mps = MPSConfig()
session = mps.session

state = { "crates": {} }
for crate in session.query(models.Crate).all():
  crate_dict = { "slots": {} }
  state["crates"][crate.number] = crate_dict
  
#Pretend these are the messages we get from link nodes.
messages = []
messages.append({"application_type": 0, "crate": 1, "slot": 1, "value": 0b0110})
#Based on the database creatd by populate-test.py, the above message should mean the following:
#Bit number: 3 2 1 0
#            -------
#            0 1 1 0

#Bit 0 = 0 means the OTR out limit switch is not engaged
#Bit 1 = 1 means the OTR in limit switch is engaged
#Bit 2 = 1 means the attenuator out limit switch is engaged
#Bit 3 = 0 means the attenuator in limit switch is not engaged
#In other words, the OTR is IN, and the attenuator is OUT.

messages.append({"application_type": 1, "crate": 1, "slot": 2, "value": 3})
#This one is way easier to understand.  The PIC has crossed threshold 3.

#Dump the info from the messages into the raw machine state data structure
for message in messages:
  crate_num = message["crate"]
  slot_num = message["slot"]
  state["crates"][crate_num]["slots"][slot_num] = message["value"]

#TODO: Iterate through the mesages and ensure the application type in the message matches what the databse tells us to expect for the crate and slot.


def get_value_for_channel(channel):
  card = channel.card
  crate = card.crate
  slot = card.slot_number
  # Extract the right bits from the message
  message = state["crates"][crate.number]["slots"][card.slot_number]
  mask = 1 << (card.type.channel_size - 1) #Something like 0100 if channel size was 3
  mask = mask | (mask - 1) # Should give something like 0111.  If mask starts out as zero this will be all ones, which will be a bad bug.  Ensure mask > 0 before this step.
  mask = mask << channel.number #Should give something like 1110 if the channel number was 1
  masked_message = message & mask
  bit_val = masked_message >> channel.number
  return bit_val
  
device_states = {}
#Turn the raw machine state into device states for all the digital devices
for device in session.query(models.DigitalDevice).all():
  device_val = 0
  for device_input in device.inputs:
    channel = device_input.channel
    bit_val = get_value_for_channel(device_input.channel)
    #The next line only works for digital devices - it assumes that the channel size is 1.
    device_val = device_val | (bit_val << device_input.bit_position)
  print("Device: {0} is in a state with a value of {1}".format(device.name, bin(device_val)))
  device_states[device.id] = device_val

#Do the same thing for analog devices.  This is was easier, because there is only one channel per device.
for device in session.query(models.AnalogDevice).all():
  device_val = get_value_for_channel(device.channel)
  print("Device: {0} has crossed threshold {1}".format(device.name, device_val))
  device_states[device.id] = device_val

#Evaluate faults.  This script queries the database to find the right fault state, and the allowed classes.
# In the real central node evaluation, this info all needs to be in look-up tables in memory.
fault_results = {}
for fault in session.query(models.Fault).all():
  fault_value = fault.fault_value(device_states)
  print("Fault: {0}.  Value: {1}".format(fault.name, fault_value))
  fault_state = session.query(models.DigitalFaultState).filter(models.DigitalFaultState.fault_id==fault.id).filter(models.DigitalFaultState.value==fault_value).one()
  fault_results[fault.name] = fault_state.name
  print("State is: {0}".format(fault_state.name))
  for md in session.query(models.MitigationDevice).all():
    allowed_classes = session.query(models.AllowedClass).filter(models.AllowedClass.fault_state_id==fault_state.id).filter(models.AllowedClass.mitigation_device_id==md.id).all()
    print("Allowed classes at {mitigation_device} for this state are: {state_list}".format(mitigation_device=md.name, state_list=", ".join([c.beam_class.name for c in allowed_classes])))

for fault in session.query(models.ThresholdFault).all():
  device = fault.analog_device
  fault_state = session.query(models.ThresholdFaultState).filter(models.ThresholdFaultState.threshold_fault_id==fault.id).filter(models.ThresholdFaultState.threshold >= device_states[device.id]).order_by(models.ThresholdFaultState.threshold).first()
  fault_results[fault.name] = "crossed threshold {0}".format(fault_state.threshold)
  for md in session.query(models.MitigationDevice).all():
    allowed_classes = session.query(models.AllowedClass).filter(models.AllowedClass.fault_state_id==fault_state.id).filter(models.AllowedClass.mitigation_device_id==md.id).all()
    print("Allowed classes at {mitigation_device} for this threshold are: {state_list}".format(mitigation_device=md.name, state_list=", ".join([c.beam_class.name for c in allowed_classes])))
  
print fault_results