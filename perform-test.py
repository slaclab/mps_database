from mps_config import MPSConfig, models

#Use the database to make a machine state data structure.
#Note that this is probably the single most inefficient way to do this.
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

#Pretend these are the messages we get from link nodes
messages = []
messages.append({"node": 1, "card": 1, "channel": 0, "value": 1})
messages.append({"node": 1, "card": 1, "channel": 1, "value": 0})
messages.append({"node": 1, "card": 1, "channel": 2, "value": 1})
messages.append({"node": 1, "card": 1, "channel": 3, "value": 0})

#Dump the info from the messages into the raw machine state data structure
for message in messages:
  state["nodes"][message["node"]]["cards"][message["card"]]["channels"][message["channel"]] = message["value"]

#Turn the raw machine state into device states
device_states = {}
for device in session.query(models.Device).all():
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
  fault_value = 0
  for fault_input in fault.inputs:
    bit_length = len(fault_input.device.inputs)
    bit_position = fault_input.bit_position
    input_value = device_states[fault_input.device_id]
    fault_value = fault_value | (input_value << (bit_length*bit_position))
  print("Fault: {0}.  Value: {1}".format(fault.name, fault_value))
  fault_state = session.query(models.FaultState).filter(models.FaultState.fault_id==fault.id).filter(models.FaultState.value==fault_value).one()
  fault_results[fault.name] = fault_state.name
  print("State is: {0}".format(fault_state.name))
print fault_results