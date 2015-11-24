from mps_config import MPSConfig, models

#Use the database to make an empty machine state data structure.
#This code is pretty inefficient.
mps = MPSConfig()
session = mps.session
state = { "nodes": {} }
for node in session.query(models.LinkNode).all():
  new_node = { "cards": {} }
  for card in node.cards:
    new_card = { "channels": {} }
    for channel in card.channels:
      new_card["channels"][channel.number] = None
    new_node["cards"][card.number] = new_card
  state["nodes"][node.number] = new_node

#Pretend these are the messages we get from link nodes.
messages = []
messages.append({"node": 1, "card": 1, "channel": 0, "value": 0})
messages.append({"node": 1, "card": 1, "channel": 1, "value": 1})
messages.append({"node": 1, "card": 1, "channel": 2, "value": 1})
messages.append({"node": 1, "card": 1, "channel": 3, "value": 0})

#Dump the info from the messages into the raw machine state data structure
for message in messages:
  state["nodes"][message["node"]]["cards"][message["card"]]["channels"][message["channel"]] = message["value"]

#Turn the raw machine state into device states
device_states = {}
for device in session.query(models.DigitalDevice).all():
  device_val = 0
  for device_input in device.inputs:
    channel = device_input.channel
    card = channel.card
    node = card.link_node
    bit_val = state["nodes"][node.number]["cards"][card.number]["channels"][channel.number]
    device_val = device_val | (bit_val << device_input.bit_position)
  device_states[device.id] = device_val

#Evaluate faults
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
print fault_results