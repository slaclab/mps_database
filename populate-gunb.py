from mps_config import MPSConfig, models
from sqlalchemy import MetaData
#The MPSConfig object points to our database file.
conf = MPSConfig()

#Clear everything out of the database.
conf.clear_all()

#session is a connection to that database.
session = conf.session

#First lets define our mitigation devices.
shutter = models.MitigationDevice(name="Shutter")
aom = models.MitigationDevice(name="AOM")
llrf = models.MitigationDevice(name="LLRF")
session.add_all([shutter, aom, llrf])

#Make some beam classes.
class_0 = models.BeamClass(number=0,name="Class ZERO")
class_1 = models.BeamClass(number=1,name="Class 1")
class_2 = models.BeamClass(number=2,name="Class 2")
class_3 = models.BeamClass(number=3,name="Class 3")
session.add_all([class_0, class_1, class_2, class_3])

#Make a crate for BPMs
crate1 = models.Crate(number=1, shelf_number=1, num_slots=6)
session.add(crate1)

#Make a crate for mitigation LN
crate2 = models.Crate(number=2, shelf_number=1, num_slots=6)
session.add(crate2)

#Define a mixed-mode link node (One digital AMC only)
mixed_link_node_type = models.ApplicationType(name="Mixed Mode Link Node", number=0, digital_channel_count=7, digital_channel_size=1, analog_channel_count=0, analog_channel_size=1)

#Define a mitigation link node (no inputs?)
mitigation_link_node_type = models.ApplicationType(name="Mitigation Link Node", number=2, digital_channel_count=0, digital_channel_size=0, analog_channel_count=0, analog_channel_size=0)

session.add_all([mixed_link_node_type, mitigation_link_node_type])

#Add one application for everything...
global_app = models.Application(global_id=100,name="MyGlobalApp",description="Generic Application")
session.add(global_app)

#Install a mixed-mode link node card in the crate.
link_node_card = models.ApplicationCard(number=1)
link_node_card.type = mixed_link_node_type
link_node_card.slot_number = 2
crate1.cards.append(link_node_card)
session.add(link_node_card)

#Define some channels for the card.
# channel 0 - YAG out switch
# channel 1 - YAG in switch
# channel 2 - Gun temperature
# channel 3 - Waveguide temperature
# channel 4 - Buncher temperature
# channel 5 - SOL01 temperature
# channel 6 - SOL02 temperature
# channel 7 - SOL01 flow
# channel 8 - SOL02 flow
# channel 9 - SOL01 current
# channel 10 - SOL02 current
# channel 11 - VVR01 vacuum status
# channel 12 - VVR02 vacuum status
digital_chans = []
chan_name = ["YAG01_OUT_SWITCH", "YAG01_IN_SWITCH", "GUN_TEMP",
             "WAVEGUIDE_TEMP", "BUNCHER_TEMP", "SOL01_TEMP", "SOL02_TEMP"]
for i in range(0,7):
  chan = models.DigitalChannel(number=i)
  chan.name =chan_name[i]
  chan.card = link_node_card
  digital_chans.append(chan)
  session.add(chan)

# Add device types
profmon_device_type = models.DeviceType(name="Profile Monitor")
session.add(profmon_device_type)

solenoid_device_type = models.DeviceType(name="Solenoid")
session.add(solenoid_device_type)

temperature_device_type = models.DeviceType(name="Temperature")
session.add(temperature_device_type)

# Define some states for the profile monitor device type
screen_out = models.DeviceState(name="Out")
screen_out.device_type = profmon_device_type
screen_out.value = 1

screen_in = models.DeviceState(name="In")
screen_in.device_type = profmon_device_type
screen_in.value = 2

screen_moving = models.DeviceState(name="Moving")
screen_moving.device_type = profmon_device_type
screen_moving.value = 0

screen_broken = models.DeviceState(name="Broken")
screen_broken.device_type = profmon_device_type
screen_broken.value = 3

session.add_all([screen_out, screen_in, screen_moving, screen_broken])
session.commit()

#Add YAG01 device
screen = models.DigitalDevice(name="YAG01", z_position=-28.061394, description="YAG Screen")
screen.device_type = profmon_device_type
screen.application = global_app
session.add(screen)

# SOL01 device
#sol1 = models.DigitalDevice(name="SOL01", z_position=-32.115049, description="Solenoid")
#sol1.device_type = solenoid_device_type
#sol1.application = global_app
#session.add(sol1)

# SOL02 device
#sol2 = models.DigitalDevice(name="SOL02", z_position=-27.538278, description="Solenoid")
#sol2.device_type = solenoid_device_type
#sol2.application = global_app
#session.add(sol2)

#Give the device some inputs.  It has in and out limit switches.
#Connect these limit switches to channels 0 and 1 of our link node card.
yag_out_lim_sw = models.DeviceInput()
yag_out_lim_sw.channel = digital_chans[0]
yag_out_lim_sw.bit_position = 0
yag_out_lim_sw.digital_device = screen
session.add(yag_out_lim_sw)

yag_in_lim_sw = models.DeviceInput()
yag_in_lim_sw.channel = digital_chans[1]
yag_in_lim_sw.bit_position = 1
yag_in_lim_sw.digital_device = screen
session.add(yag_in_lim_sw)

#Configure faults for the device
yag_fault = models.Fault(name="YAG01 Profile Monitor Fault")
session.add(yag_fault)

#This fault only has one input: the device state.
yag_fault_input = models.FaultInput()
yag_fault_input.bit_position = 0
yag_fault_input.device = screen
yag_fault_input.fault = yag_fault
session.add(yag_fault_input)

#This fault's states match up exactly with the device states.
#yag_fault_out = models.DigitalFaultState(name="Out")
#yag_fault_out.fault = yag_fault
#yag_fault_out.value = 1
#session.add(yag_fault_out)
yag_fault_in = models.DigitalFaultState()
yag_fault_in.device_state = screen_in
yag_fault_in.fault = yag_fault
session.add(yag_fault_in)

yag_fault_moving = models.DigitalFaultState()
yag_fault_moving.fault = yag_fault
yag_fault_moving.device_state = screen_moving
session.add(yag_fault_moving)

yag_fault_broken = models.DigitalFaultState()
yag_fault_broken.fault = yag_fault
yag_fault_broken.device_state = screen_broken
session.add(yag_fault_broken)

#Give the YAG01 fault states allowed beam classes.
yag_fault_in.add_allowed_class(beam_class=class_1, mitigation_device=aom)
yag_fault_moving.add_allowed_class(beam_class=class_0, mitigation_device=shutter)
yag_fault_broken.add_allowed_class(beam_class=class_0, mitigation_device=shutter)

session.commit()

#================================================================================
#Add Gun Temperature input device
gun_temperature = models.DigitalDevice(name="Gun Temperature")
gun_temperature.device_type = temperature_device_type
gun_temperature.application = global_app
gun_temperature.z_position = 0
gun_temperature.description = "Gun Temperature Summary Input"
session.add(gun_temperature)

# Give the Gun Temperature its single input channel
gun_temperature_channel = models.DeviceInput()
gun_temperature_channel.channel = digital_chans[2]
gun_temperature_channel.bit_position = 0
gun_temperature_channel.digital_device = gun_temperature
session.add(gun_temperature_channel)
#================================================================================

#================================================================================
#Add Waveguide Temperature input device
wg_temperature = models.DigitalDevice(name="Waveguide Temperature")
wg_temperature.device_type = temperature_device_type
wg_temperature.application = global_app
wg_temperature.z_position = 0
wg_temperature.description = "Waveguide Temperature Summary Input"
session.add(wg_temperature)

# Give the Waveguide Temperature its single input channel
wg_temperature_channel = models.DeviceInput()
wg_temperature_channel.channel = digital_chans[3]
wg_temperature_channel.bit_position = 0
wg_temperature_channel.digital_device = wg_temperature
session.add(wg_temperature_channel)
#================================================================================

#================================================================================
#Add Buncher Temperature input device
buncher_temperature = models.DigitalDevice(name="Buncher Temperature")
buncher_temperature.device_type = temperature_device_type
buncher_temperature.application = global_app
buncher_temperature.z_position = -30.299721
buncher_temperature.description = "Buncher Temperature Summary Input"
session.add(buncher_temperature)

# Give the Buncher Temperature its single input channel
buncher_temperature_channel = models.DeviceInput()
buncher_temperature_channel.channel = digital_chans[4]
buncher_temperature_channel.bit_position = 0
buncher_temperature_channel.digital_device = buncher_temperature
session.add(buncher_temperature_channel)
#================================================================================

#================================================================================
#Add SOL01 Temperature input device
sol1_temperature = models.DigitalDevice(name="SOL01", z_position=-32.115049, description="SOL01 Temperature")
#sol1_temperature = models.DigitalDevice(name="SOL01 Temperature")
sol1_temperature.device_type = temperature_device_type
sol1_temperature.application = global_app
session.add(sol1_temperature)

# Give the SOL01 Temperature its single input channel
sol1_temperature_channel = models.DeviceInput()
sol1_temperature_channel.channel = digital_chans[5]
sol1_temperature_channel.bit_position = 0
sol1_temperature_channel.digital_device = sol1_temperature
session.add(sol1_temperature_channel)
#================================================================================

#================================================================================
#Add SOL02 Temperature input device
sol2_temperature = models.DigitalDevice(name="SOL02", z_position=-27.538278, description="SOL02 Temperature")
#sol_temperature = models.DigitalDevice(name="SOL01/SOL02 Temperature")
sol2_temperature.device_type = temperature_device_type
sol2_temperature.application = global_app
session.add(sol2_temperature)

# Give the SOL02 Temperature its single input channel
sol2_temperature_channel = models.DeviceInput()
sol2_temperature_channel.channel = digital_chans[6]
sol2_temperature_channel.bit_position = 0
sol2_temperature_channel.digital_device = sol2_temperature
session.add(sol2_temperature_channel)
#================================================================================

# Configure Faults for Temperature input devices (used for Gun/Waveguide/Buncher/Solenoid temperature)
gun_temperature_fault = models.Fault(name="Gun Temperature Fault")
session.add(gun_temperature_fault)

wg_temperature_fault = models.Fault(name="Waveguide Temperature Fault")
session.add(wg_temperature_fault)

buncher_temperature_fault = models.Fault(name="Buncher Temperature Fault")
session.add(buncher_temperature_fault)

sol1_temperature_fault = models.Fault(name="SOL01 Temperature Fault")
session.add(sol1_temperature_fault)

sol2_temperature_fault = models.Fault(name="SOL02 Temperature Fault")
session.add(sol2_temperature_fault)

# Temperature Fault Inputs
temperature_fault_input = models.FaultInput()
temperature_fault_input.bit_position = 0
temperature_fault_input.device = gun_temperature
temperature_fault_input.fault = gun_temperature_fault
session.add(temperature_fault_input)
temperature_fault_input = models.FaultInput()
temperature_fault_input.bit_position = 0
temperature_fault_input.device = wg_temperature
temperature_fault_input.fault = wg_temperature_fault
session.add(temperature_fault_input)
temperature_fault_input = models.FaultInput()
temperature_fault_input.bit_position = 0
temperature_fault_input.device = buncher_temperature
temperature_fault_input.fault = buncher_temperature_fault
session.add(temperature_fault_input)
temperature_fault_input = models.FaultInput()
temperature_fault_input.bit_position = 0
temperature_fault_input.device = sol1_temperature
temperature_fault_input.fault = sol1_temperature_fault
session.add(temperature_fault_input)
temperature_fault_input = models.FaultInput()
temperature_fault_input.bit_position = 0
temperature_fault_input.device = sol2_temperature
temperature_fault_input.fault = sol2_temperature_fault
session.add(temperature_fault_input)

# Fault state for Temperature
temperature_device_fault = models.DeviceState(name="Temperature Fault")
temperature_device_fault.device_type = temperature_device_type
temperature_device_fault.value = 1
session.add(temperature_device_fault)

temperature_device_ok = models.DeviceState(name="Temperature OK")
temperature_device_fault.device_type = temperature_device_type
temperature_device_fault.value = 0
session.add(temperature_device_fault)

gun_temperature_fault_state = models.DigitalFaultState()
gun_temperature_fault_state.fault = gun_temperature_fault
gun_temperature_fault_state.device_state = temperature_device_fault
session.add(gun_temperature_fault_state)
gun_temperature_fault_state.add_allowed_class(beam_class=class_0, mitigation_device=shutter)

wg_temperature_fault_state = models.DigitalFaultState()
wg_temperature_fault_state.fault = wg_temperature_fault
wg_temperature_fault_state.device_state = temperature_device_fault
session.add(wg_temperature_fault_state)
wg_temperature_fault_state.add_allowed_class(beam_class=class_0, mitigation_device=shutter)

buncher_temperature_fault_state = models.DigitalFaultState()
buncher_temperature_fault_state.fault = buncher_temperature_fault
buncher_temperature_fault_state.device_state = temperature_device_fault
session.add(buncher_temperature_fault_state)
buncher_temperature_fault_state.add_allowed_class(beam_class=class_0, mitigation_device=shutter)

sol1_temperature_fault_state = models.DigitalFaultState()
sol1_temperature_fault_state.fault = sol1_temperature_fault
sol1_temperature_fault_state.device_state = temperature_device_fault
session.add(sol1_temperature_fault_state)
sol1_temperature_fault_state.add_allowed_class(beam_class=class_0, mitigation_device=shutter)

sol2_temperature_fault_state = models.DigitalFaultState()
sol2_temperature_fault_state.fault = sol2_temperature_fault
sol2_temperature_fault_state.device_state = temperature_device_fault
session.add(sol2_temperature_fault_state)
sol2_temperature_fault_state.add_allowed_class(beam_class=class_0, mitigation_device=shutter)

session.commit()
