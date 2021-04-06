from mps_database.mps_config import MPSConfig, models
from sqlalchemy import MetaData
#The MPSConfig object points to our database file.
conf = MPSConfig(filename="huge.db")

#Clear everything out of the database.
conf.clear_all()

numMitigationDevices = 5
numChannels = 5000
channelsPerCrate = 50
#numChannels = 10
#channelsPerCrate = 10
numCrates = numChannels / channelsPerCrate
numCards = numCrates # Yep, one card per crate
channelsPerCard = channelsPerCrate
channelsPerDevice = 2 # e.g. IN and OUT switch
devicesPerCard = channelsPerCard / channelsPerDevice
numBeamClasses = 2**(2**channelsPerDevice)

session = conf.session

# Mitigation Devices
mitigationDevices=[]
for i in range(0, numMitigationDevices):
  device = models.MitigationDevice(name="Device " + str(i))
  mitigationDevices.append(device)
  session.add(device)

# Beam Classes
beamClasses=[]
for i in range(0, numBeamClasses):
  device = models.BeamClass(number=i, name="Class " + str(i))
  beamClasses.append(device)
  session.add(device)

# Crates
crates=[]
for i in range(0, numCrates):
  device = models.Crate(number=i, shelf_number=1, num_slots=6)
  crates.append(device)
  session.add(device)

# Define a mixed-mode link node (One digital AMC, no analogs)
mixed_link_node_type = models.ApplicationType(name="Mixed Mode Link Node", number=0,
                                              digital_channel_count=channelsPerCrate,
                                              digital_channel_size=1, analog_channel_count=0,
                                              analog_channel_size=1)

# Define a mitigation link node
mitigation_link_node_type = models.ApplicationType(name="Mitigation Link Node", number=1,
                                                   digital_channel_count=0, digital_channel_size=0,
                                                   analog_channel_count=0, analog_channel_size=0)

session.add_all([mixed_link_node_type, mitigation_link_node_type])

#Add one application for everything...
global_app = models.Application(global_id=100,name="MyGlobalApp",description="Generic Application")
session.add(global_app)

# Install a mixed-mode link node card in every crate.
cards=[]
for i in range(0, numCrates):
  link_node_card = models.ApplicationCard(number=i, type=mixed_link_node_type, slot_number=2)
  cards.append(link_node_card)
  crates[i].cards.append(link_node_card)
  session.add(link_node_card)

# Define some channels for the cards
channels=[]
for i in range(0, numCards):
  for j in range(0, channelsPerCard):
    channel = models.DigitalChannel(number=j)
    channel.name = "Channel " + str(i) + ":" + str(j)
    channel.card = cards[i]
    channels.append(channel)
    session.add(channel)

# Define a device type
digitalDeviceType = models.DeviceType(name="Generic Device Type")
session.add(digitalDeviceType)

faultDigitalDeviceType = models.DeviceType(name="Composed Device Type")
session.add(faultDigitalDeviceType)

# States for the device - these are not really used 
#deviceStates=[]
#for i in range(0, 2**channelsPerDevice):
#  deviceState = models.DeviceState(name="State " + str(i),
#                                   device_type=digitalDeviceType,
#                                   value=i)
#  deviceStates.append(deviceState)
#  session.add(deviceState)

# States for the faults
# 2 sets of 2**channelsPerDevice
faultDeviceStates=[]
for i in range(0, 2 ** (2**channelsPerDevice)):
  faultDeviceState = models.DeviceState(name="FaultState " + str(i),
                                        device_type=faultDigitalDeviceType,
                                        value=i)
  faultDeviceStates.append(faultDeviceState)
  session.add(faultDeviceState)

# Add digital devices
devices=[]
for i in range(0, numCards):
  for j in range(0, devicesPerCard):
    device = models.DigitalDevice(name="Device " + str(i) + ":" + str(j),
                                  z_position=i*devicesPerCard + j,
                                  description="Device #" + str(j) + " for card #" + str(i),
                                  device_type = digitalDeviceType, application = global_app)
    devices.append(device)
    session.add(device)

# Assign inputs to devices
for i in range(0, len(devices)):
  for j in range(0, channelsPerDevice):
    deviceInput = models.DeviceInput(channel=channels[i*channelsPerDevice+j],
                                     bit_position=j, digital_device=devices[i])
    session.add(deviceInput)

# Configure faults - each fault is the result of the inputs from neighboring devices
# each one has two bits as input
numFaults = devicesPerCard - 1
faults=[]
faultStates=[]
for i in range(0, numCards):
  for j in range(0, numFaults):
    fault = models.Fault(name="Fault card #" + str(i) + " devices #" + str(j) + "/" + str(j+1))
    faults.append(fault)
    session.add(fault)
    faultInput0 = models.FaultInput(bit_position=0, device=devices[j], fault=fault) # 2 bits for first input
    faultInput1 = models.FaultInput(bit_position=2, device=devices[j+1], fault=fault) # 2 bits for the next input
    session.add_all([faultInput0, faultInput1])

    # Add fault states, and allowed beam class - one for each DeviceState
    for k in range(0, len(faultDeviceStates)):
      faultState = models.FaultState(device_state=faultDeviceStates[k], fault=fault)
      faultStates.append(faultState)
      session.add(faultState)
      faultState.add_allowed_class(beam_class=beamClasses[k], mitigation_device=mitigationDevices[0])

# Add same ignore logic - If fault #0 -> ignore fault #1; if fault #2 -> ignore fault #3 ... so on
for i in range(0,len(faults)):
  if (i % 2 == 0):
    condition = models.Condition(name="Condition #" + str(i),
                                 description="Condition for fault state",
                                 value=1)
    session.add(condition)

    # The input for the condition is the first state listed for the fault
    conditionInput = models.ConditionInput(bit_position=0, fault_state=faults[i].states[0],
                                           condition=condition)
    session.add(conditionInput)

    # The ignored condition/fault state is the last state of the next fault - yeah, non-sense and complicated
    ignoreCondition = models.IgnoreCondition(condition=condition, fault_state=faults[i+1].states[len(faults[i+1].states)-1])
    session.add(ignoreCondition)

session.commit()

#
# Create test file
#
f = open("inputs-huge.txt", "w")
f.write('Inputs {0} 0\n'.format(numChannels))
value = 0
for i in range(1, numChannels+1):
  f.write('{0} {1}\n'.format(i, value))
  if (value == 0):
    value = 1
  else:
    value = 0
f.close()
