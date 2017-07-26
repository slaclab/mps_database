#!/usr/bin/env python
from mps_config import MPSConfig, models
from sqlalchemy import MetaData
#The MPSConfig object points to our database file.
conf = MPSConfig()


#Clear everything out of the database.
conf.clear_all()

#session is a connection to that database.
session = conf.session

#First lets define our mitigation devices.
shutter = models.MitigationDevice(name="MS", description="Mechanical Shutter", destination_mask=0x01)
aom = models.MitigationDevice(name="AOM", description="AOM", destination_mask=0x02)
session.add_all([shutter, aom])

#Make some beam classes.
class_0 = models.BeamClass(number=0,name="Power Class 0",description="No Beam",
                              integration_window=10, total_charge=100, min_period=1)
class_1 = models.BeamClass(number=1,name="Power Class 1",description="YAG Max Power",
                              integration_window=10, total_charge=100, min_period=1)
class_2 = models.BeamClass(number=2,name="Power Class 2",description="Full Power",
                              integration_window=10, total_charge=100, min_period=1)
session.add_all([class_0, class_1, class_2])

# EIC Link Node - L2KA00-05 (Level 17)
# Make a crate for BPMs, and for the mitigation LN
crate = models.Crate(number=1, shelf_number=1, num_slots=8, location="L2KA00", rack="05", elevation=17)
session.add_all([crate])

#Define a mixed-mode link node (One digital AMC, one analog for IM01/SOL01-02 Curr/Faraday Cup Curr)
eic_digital_app = models.ApplicationType(name="Digital Card", number=0,
                                            digital_channel_count=9, digital_channel_size=1,
                                            analog_channel_count=0, analog_channel_size=1)
eic_bpm_app = models.ApplicationType(name="BPM Card", number=1,
                                      digital_channel_count=0, digital_channel_size=1,
                                      analog_channel_count=2, analog_channel_size=1)
eic_analog_app = models.ApplicationType(name="AMC Analog Card", number=2,
                                      digital_channel_count=0, digital_channel_size=1,
                                      analog_channel_count=3, analog_channel_size=1)

session.add_all([eic_digital_app, eic_bpm_app, eic_analog_app])

# Application Cards (one for digital inputs, three for analog inputs)
link_node_card = models.ApplicationCard(name="EIC Digital Inputs", number=100, area="GUNB",
                                        location="MP10", type=eic_digital_app, slot_number=2,
                                        global_id=0, description="EIC Digital Status")
sol_card = models.ApplicationCard(name="EIC Analog Inputs", number=104, area="GUNB",
                                  location="MP11", type=eic_analog_app, slot_number=2, amc=1,
                                  global_id=1, description="EIC Digital Status")
bpm_card = models.ApplicationCard(name="EIC BPM01/BPM02", number=101, area="GUNB", 
                                  location="MP12", type=eic_bpm_app, slot_number=3,
                                  global_id=2, description="EIC BPM Status")
im_card = models.ApplicationCard(name="EIC IM01", number=102, area="GUNB",
                                 location="MP13", type=eic_analog_app, slot_number=6,
                                 global_id=3, description="EIC IM Status")
fc_card = models.ApplicationCard(name="EIC FC01", number=103, area="GUNB",
                                 location="MP14", type=eic_analog_app, slot_number=7,
                                 global_id=4, description="EIC Faraday Cup Status")

crate.cards.append(link_node_card)
crate.cards.append(sol_card)
crate.cards.append(bpm_card)
crate.cards.append(im_card)
crate.cards.append(fc_card)

session.add_all([link_node_card, bpm_card, im_card, fc_card])

#Define some channels for the card.
# channel 0 - YAG01 out switch
# channel 1 - YAG01 in switch
# channel 2 - Gun temperature
# channel 3 - Waveguide temperature
# channel 4 - Buncher temperature
# channel 5 - SOL01 temperature
# channel 6 - SOL02 temperature
# channel 7 - VVR01 vacuum status
# channel 8 - VVR02 vacuum status
digital_chans = []

names=[]
#===========  device, zero name, one name, fault state
names.append(("OUT_LMTSW", "IS_OUT", "NOT_OUT", 1))
names.append(("IN_LMTSW", "IS_IN", "NOT_IN", 1))
names.append(("GUN_TEMP", "IS_FAULTED", "IS_OK", 0))
names.append(("WAVEGUIDE_TEMP", "IS_FAULTED", "IS_OK", 0))
names.append(("BUNCHER_TEMP", "IS_FAULTED", "IS_OK", 0))
names.append(("SOL01_TEMP", "IS_FAULTED", "IS_OK", 0))
names.append(("SOL02_TEMP", "IS_FAULTED", "IS_OK", 0))
names.append(("VVR01_VAC", "IS_FAULTED", "IS_OK", 0))
names.append(("VVR02_VAC", "IS_FAULTED", "IS_OK", 0))

for i in range(0,9):
  chan = models.DigitalChannel(number=i)
  (name, z_name, o_name, alarm_state) = names[i]
  chan.name = name
  chan.z_name = z_name
  chan.o_name = o_name
  chan.alarm_state = alarm_state
  chan.card = link_node_card
  digital_chans.append(chan)
  session.add(chan)

im01_channel = models.AnalogChannel(name="IM01 Charge", number=0, card = im_card)
fc_channel = models.AnalogChannel(name="Faraday Cup Current", number=0, card = fc_card)
sol01_channel = models.AnalogChannel(name="SOL01 Current", number=0, card = sol_card)
sol02_channel = models.AnalogChannel(name="SOL02 Current", number=1, card = sol_card)
bpm01_channel = models.AnalogChannel(name="BPM01", number=0, card = bpm_card)
bpm02_channel = models.AnalogChannel(name="BPM02", number=1, card = bpm_card)

session.add_all([im01_channel, fc_channel,
                 sol01_channel, sol02_channel, 
                 bpm01_channel, bpm02_channel])

# Add digital device types
profmon_device_type = models.DeviceType(name="PROF", description="Profile Monitor")
temp_device_type = models.DeviceType(name="TEMP", description="Temperature Status")
vvr_device_type = models.DeviceType(name="VVPR", description="Vacuum Pneumatic Rouhing Valve Status")
session.add_all([profmon_device_type, temp_device_type, vvr_device_type])

# Add analog device types
im_device_type = models.DeviceType(name="TORO", description="Toroid") #units="uC")
fc_device_type = models.DeviceType(name="FARC", description="Faraday Cup") #units="mA")
sol_curr_device_type = models.DeviceType(name="SOLN", description="Solenoid") #units="mA")
session.add_all([im_device_type, fc_device_type, sol_curr_device_type])

bpm_device_type = models.DeviceType(name="BPMS", description="Beam Position Monitor")
session.add_all([bpm_device_type])

# Define some states for the device types
screen_out        = models.DeviceState(name="Out", device_type = profmon_device_type, value = 2)
screen_in         = models.DeviceState(name="In", device_type = profmon_device_type, value = 1)
screen_moving     = models.DeviceState(name="Moving", device_type = profmon_device_type, value = 3)
screen_broken     = models.DeviceState(name="Broken", device_type = profmon_device_type, value = 0)
temp_device_fault = models.DeviceState(name="Temp Fault", device_type = temp_device_type, value = 0)
temp_device_ok    = models.DeviceState(name="Temp OK", device_type = temp_device_type, value = 1)
vvr_device_fault  = models.DeviceState(name="Vacuum Fault", device_type = vvr_device_type, value = 0)
vvr_device_ok     = models.DeviceState(name="Vacuum OK", device_type = vvr_device_type, value = 1)
session.add_all([screen_out, screen_in, screen_moving, screen_broken,
                 temp_device_fault, temp_device_ok,
                 vvr_device_fault, vvr_device_ok])

#
# BPM DeviceStates - Threshold States
#
# There are 8 comparators for each X, Y and TMIT. Each comparator checks if
# the measurement in within the low and high thresholds. If a bit is set
# it means the measured value is outside the low/high window.
#
# Only 4 of the 8 thresholds are used for BPM01/BPM02, but they are all added
#
#bpm_states=[]
bpm_x_states=[]
bpm_y_states=[]
bpm_t_states=[]
state_value = 1
# X Thresholds - bits 0 through 7
for i in range(0,8):
  state_name = "X_T" + str(i)
  bpm_threshold_state = models.DeviceState(name=state_name, value=state_value, mask=state_value, device_type = bpm_device_type)
  if (i < 8):
    bpm_x_states.append(bpm_threshold_state)
  session.add(bpm_threshold_state)
  state_value = (state_value << 1)
# Y Thresholds - bits 8 through 15
for i in range(0,8):
  state_name = "Y_T" + str(i)
  bpm_threshold_state = models.DeviceState(name=state_name, value=state_value, mask=state_value, device_type = bpm_device_type)
  if (i < 8):
    bpm_y_states.append(bpm_threshold_state)
  session.add(bpm_threshold_state)
  state_value = (state_value << 1)
# TMIT Thresholds - bits 16 though 23
for i in range(0,8):
  state_name = "T_T" + str(i)
  bpm_threshold_state = models.DeviceState(name=state_name, value=state_value, mask=state_value, device_type = bpm_device_type)
  if (i < 8):
    bpm_t_states.append(bpm_threshold_state)
  session.add(bpm_threshold_state)
  state_value = (state_value << 1)

session.commit()

# Other device states for analog devices, they are all grouped here.
# Defining two comparators for each of the four integrators for IM01
# Only two comparators for the first integrator for devices SOL01, SOL02 and FC
im_int1_states=[]
im_int2_states=[]
im_int3_states=[]
im_int4_states=[]
sol1_int1_states=[]
sol2_int1_states=[]
fc_int1_states=[]

state_value = 1
# Integrator #1 - bits 0 through 7
for i in range(0,8):
  state_name = "INT1_T" + str(i)
  threshold_state = models.DeviceState(name=state_name, value=state_value, mask=state_value, device_type = im_device_type)
  sol1_int1_state = models.DeviceState(name=state_name, value=state_value, mask=state_value, device_type = im_device_type)
  sol2_int1_state = models.DeviceState(name=state_name, value=state_value, mask=state_value, device_type = im_device_type)
  fc_int1_state = models.DeviceState(name=state_name, value=state_value, mask=state_value, device_type = im_device_type)
  if (i < 2):
    im_int1_states.append(threshold_state)
    sol1_int1_states.append(sol1_int1_state)
    sol2_int1_states.append(sol2_int1_state)
    fc_int1_states.append(fc_int1_state)
  session.add(threshold_state)
  session.add(sol1_int1_state)
  session.add(sol2_int1_state)
  session.add(fc_int1_state)
  state_value = (state_value << 1)
# Integrator #2 - bits 8 through 15
for i in range(0,8):
  state_name = "INT2_T" + str(i)
  threshold_state = models.DeviceState(name=state_name, value=state_value, mask=state_value, device_type = im_device_type)
  if (i < 2):
    im_int2_states.append(threshold_state)
  session.add(threshold_state)
  state_value = (state_value << 1)
# Integrator #3 - bits 16 though 23
for i in range(0,8):
  state_name = "INT3_T" + str(i)
  threshold_state = models.DeviceState(name=state_name, value=state_value, mask=state_value, device_type = im_device_type)
  if (i < 2):
    im_int3_states.append(threshold_state)
  session.add(threshold_state)
  state_value = (state_value << 1)
# Integrator #4 - bits 24 though 32
for i in range(0,8):
  state_name = "INT4_T" + str(i)
  threshold_state = models.DeviceState(name=state_name, value=state_value, mask=state_value, device_type = im_device_type)
  if (i < 2):
    im_int4_states.append(threshold_state)
  session.add(threshold_state)
  state_value = (state_value << 1)

session.commit()

#Add digital devices
screen = models.DigitalDevice(name="YAG01", position=855, description="YAG Screen",
                              device_type = profmon_device_type, card = link_node_card, area="GUNB")
gun_temp = models.DigitalDevice(name="Gun Temperature", device_type = temp_device_type,
                                card = link_node_card, position = 100,
                                description = "Gun Temperature Summary Input", area="GUNB")
wg_temp = models.DigitalDevice(name="Waveguide Temperature", device_type = temp_device_type,
                               card = link_node_card, position = 150,
                               description = "Waveguide Temperature Summary Input", area="GUNB")
buncher_temp = models.DigitalDevice(name="Buncher Temperature", device_type = temp_device_type,
                                    card = link_node_card, position = 200,
                                    description = "Buncher Temperature Summary Input", area="GUNB")
sol01_temp = models.DigitalDevice(name="SOL01 Temp", position=400, description="SOL01 Temperature",
                                  device_type = temp_device_type, card = link_node_card, area="GUNB")
sol02_temp = models.DigitalDevice(name="SOL02 Temp", position=900, description="SOL02 Temperature",
                                  device_type = temp_device_type, card = link_node_card, area="GUNB")
vvr1 = models.DigitalDevice(name="VVR01", position=350, description="Vacuum Gate Valve VVR01",
                                  device_type = vvr_device_type, card = link_node_card, area="GUNB")
vvr2 = models.DigitalDevice(name="VVR02", position=400, description="Vacuum Gate Valve VVR02",
                                  device_type = vvr_device_type, card = link_node_card, area="GUNB")

session.add_all([screen, gun_temp, wg_temp, buncher_temp,
                 sol01_temp, sol02_temp, vvr1, vvr2])

# Add analog devices
bpm01 = models.AnalogDevice(name="BPM01", device_type = bpm_device_type, channel=bpm01_channel,
                            card = bpm_card, position=201, description="BPM01", evaluation=1, area="GUNB")
bpm02 = models.AnalogDevice(name="BPM02", device_type = bpm_device_type, channel=bpm02_channel,
                            card =bpm_card, position=601, description="BPM02", evaluation=1, area="GUNB")
im01 = models.AnalogDevice(name="IM01", device_type=im_device_type, channel=im01_channel,
                           card=im_card, position=650, description="Toroid, ICT Charge", evaluation=1, area="GUNB")
fc = models.AnalogDevice(name="FC", device_type=fc_device_type, channel=fc_channel,
                           card=fc_card, position=900, description="Faraday Cup Current", evaluation=1, area="GUNB")
sol01 = models.AnalogDevice(name="SOL01", device_type=sol_curr_device_type, channel=sol01_channel,
                            card=sol_card, position=400, description="SOL01 Current", evaluation=1, area="GUNB")
sol02 = models.AnalogDevice(name="SOL02", device_type=sol_curr_device_type, channel=sol02_channel,
                            card=sol_card, position=900, description="SOL02 Current", evaluation=1, area="GUNB")

# Give the device some inputs.  It has in and out limit switches.
yag_out_lim_sw = models.DeviceInput(channel = digital_chans[0], bit_position = 0, digital_device = screen, fault_value=1)
yag_in_lim_sw = models.DeviceInput(channel = digital_chans[1], bit_position = 1, digital_device = screen, fault_value=1)
gun_temp_channel = models.DeviceInput(channel = digital_chans[2], bit_position = 0,
                                      digital_device = gun_temp, fault_value=0)
wg_temp_channel = models.DeviceInput(channel = digital_chans[3], bit_position = 0, digital_device = wg_temp, fault_value=0)
buncher_temp_channel = models.DeviceInput(channel = digital_chans[4], bit_position = 0,
                                          digital_device = buncher_temp, fault_value=0)
sol01_temp_channel = models.DeviceInput(channel = digital_chans[5], bit_position = 0,
                                        digital_device = sol01_temp, fault_value=0)
sol02_temp_channel = models.DeviceInput(channel = digital_chans[6], bit_position = 0,
                                        digital_device = sol02_temp, fault_value=0)
vvr1_channel =  models.DeviceInput(channel = digital_chans[7], bit_position = 0,
                                   digital_device = vvr1, fault_value=0)
vvr2_channel =  models.DeviceInput(channel = digital_chans[8], bit_position = 0,
                                   digital_device = vvr2, fault_value=0)

session.add_all([yag_out_lim_sw,yag_in_lim_sw, gun_temp_channel, wg_temp_channel,
                 buncher_temp_channel, sol01_temp_channel, sol02_temp_channel,
                 vvr1_channel, vvr2_channel])

#Configure faults for the digital devices
yag_fault = models.Fault(name="TGT", description="YAG01 Profile Monitor Screen Fault")
gun_temp_fault = models.Fault(name="GUN_TEMP", description="Gun Temperature Fault")
wg_temp_fault = models.Fault(name="WG_TEMP", description="Waveguide Temperature Fault")
buncher_temp_fault = models.Fault(name="BUNCH_TEMP", description="Buncher Temperature Fault")
sol01_temp_fault = models.Fault(name="SOL01_TEMP", description="SOL01 Temperature Fault")
sol02_temp_fault = models.Fault(name="SOL02_TEMP", description="SOL02 Temperature Fault")
vvr1_fault = models.Fault(name="VVR01", description="VVR01 Vacuum Valve Fault")
vvr2_fault = models.Fault(name="VVR02", description="VVR02 Vacuum Valve Fault")
session.add_all([yag_fault, gun_temp_fault, wg_temp_fault,
                 buncher_temp_fault, sol01_temp_fault, sol02_temp_fault,
                 vvr1_fault, vvr2_fault])

#bpm01_fault = models.Fault(name="BPM01", description="BPM01 X/Y/TMIT Threshold Fault")
#bpm02_fault = models.Fault(name="BPM02", description="BPM02 X/Y/TMIT Threshold Fault")
#session.add_all([bpm01_fault, bpm02_fault])

bpm01_x_fault = models.Fault(name="BPM01_X", description="BPM01 X Threshold Fault")
bpm01_y_fault = models.Fault(name="BPM01_Y", description="BPM01 Y Threshold Fault")
bpm01_t_fault = models.Fault(name="BPM01_T", description="BPM01 TMIT Threshold Fault")
session.add_all([bpm01_x_fault, bpm01_y_fault, bpm01_t_fault])

bpm02_x_fault = models.Fault(name="BPM02_X", description="BPM02 X Threshold Fault")
bpm02_y_fault = models.Fault(name="BPM02_Y", description="BPM02 Y Threshold Fault")
bpm02_t_fault = models.Fault(name="BPM02_T", description="BPM02 TMIT Threshold Fault")
session.add_all([bpm02_x_fault, bpm02_y_fault, bpm02_t_fault])

im01_int1_fault = models.Fault(name="IM01_I1", description="IM01 Integrator #1 Fault")
im01_int2_fault = models.Fault(name="IM01_I2", description="IM01 Integrator #2 Fault")
im01_int3_fault = models.Fault(name="IM01_I3", description="IM01 Integrator #3 Fault")
im01_int4_fault = models.Fault(name="IM01_I4", description="IM01 Integrator #4 Fault")
session.add_all([im01_int1_fault, im01_int2_fault, im01_int3_fault, im01_int4_fault])

sol1_int1_fault = models.Fault(name="SOL01_I1", description="SOL01 Integrator #1 Fault")
sol2_int1_fault = models.Fault(name="SOL02_I1", description="SOL01 Integrator #2 Fault")
fc_int1_fault = models.Fault(name="FC_I1", description="FC01 Integrator #1 Fault")
session.add_all([sol1_int1_fault, sol2_int1_fault, fc_int1_fault])

# Inputs for the digital faults
yag_fault_input = models.FaultInput(bit_position = 0, device = screen, fault = yag_fault)
gun_temp_fault_input = models.FaultInput(bit_position = 0, device = gun_temp, fault = gun_temp_fault)
wg_temp_fault_input = models.FaultInput(bit_position = 0, device = wg_temp, fault = wg_temp_fault)
buncher_temp_fault_input = models.FaultInput(bit_position = 0, device = buncher_temp, fault = buncher_temp_fault)
sol01_temp_fault_input = models.FaultInput(bit_position = 0, device = sol01_temp, fault = sol01_temp_fault)
sol02_temp_fault_input = models.FaultInput(bit_position = 0, device = sol02_temp, fault = sol02_temp_fault)
vvr1_fault_input = models.FaultInput(bit_position = 0, device = vvr1, fault = vvr1_fault)
vvr2_fault_input = models.FaultInput(bit_position = 0, device = vvr2, fault = vvr2_fault)
session.add_all([yag_fault_input, gun_temp_fault_input, wg_temp_fault_input,
                 buncher_temp_fault_input, sol01_temp_fault_input, sol02_temp_fault_input,
                 vvr1_fault, vvr2_fault])

# The bit_position is the location within the fault (bpm01_x_fault) where
# the value from the device (bpm01) will go
bpm01_x_fault_input = models.FaultInput(bit_position = 0, device = bpm01, fault = bpm01_x_fault)
bpm01_y_fault_input = models.FaultInput(bit_position = 0, device = bpm01, fault = bpm01_y_fault)
bpm01_t_fault_input = models.FaultInput(bit_position = 0, device = bpm01, fault = bpm01_t_fault)

bpm02_x_fault_input = models.FaultInput(bit_position = 0, device = bpm02, fault = bpm02_x_fault)
bpm02_y_fault_input = models.FaultInput(bit_position = 0, device = bpm02, fault = bpm02_y_fault)
bpm02_t_fault_input = models.FaultInput(bit_position = 0, device = bpm02, fault = bpm02_t_fault)

session.add_all([bpm01_x_fault_input, bpm01_y_fault_input, bpm01_t_fault_input,
                 bpm02_x_fault_input, bpm02_y_fault_input, bpm02_t_fault_input])

im01_int1_fault_input = models.FaultInput(bit_position = 0, device = im01, fault = im01_int1_fault)
im01_int2_fault_input = models.FaultInput(bit_position = 0, device = im01, fault = im01_int2_fault)
im01_int3_fault_input = models.FaultInput(bit_position = 0, device = im01, fault = im01_int3_fault)
im01_int4_fault_input = models.FaultInput(bit_position = 0, device = im01, fault = im01_int4_fault)

session.add_all([im01_int1_fault_input, im01_int2_fault_input,
                 im01_int3_fault_input, im01_int4_fault_input])

sol1_int1_fault_input = models.FaultInput(bit_position = 0, device = sol01, fault = sol1_int1_fault)
sol2_int1_fault_input = models.FaultInput(bit_position = 0, device = sol02, fault = sol2_int1_fault)
fc_int1_fault_input = models.FaultInput(bit_position = 0, device = fc, fault = fc_int1_fault)

session.add_all([sol1_int1_fault_input, sol2_int1_fault_input, fc_int1_fault_input])

# FaultStates
yag_fault_in = models.FaultState(device_state = screen_in, fault = yag_fault)
yag_fault_moving = models.FaultState(fault = yag_fault, device_state = screen_moving)
yag_fault_broken = models.FaultState(fault = yag_fault, device_state = screen_broken)
gun_temp_fault_state = models.FaultState(fault = gun_temp_fault, device_state = temp_device_fault)
wg_temp_fault_state = models.FaultState(fault = wg_temp_fault, device_state = temp_device_fault)
buncher_temp_fault_state = models.FaultState(fault = buncher_temp_fault, device_state = temp_device_fault)
sol01_temp_fault_state = models.FaultState(fault = sol01_temp_fault, device_state = temp_device_fault)
sol02_temp_fault_state = models.FaultState(fault = sol02_temp_fault, device_state = temp_device_fault)
vvr1_fault_state = models.FaultState(fault = vvr1_fault, device_state = vvr_device_fault)
vvr2_fault_state = models.FaultState(fault = vvr2_fault, device_state = vvr_device_fault)
session.add_all([yag_fault_in, yag_fault_moving, yag_fault_broken,
                 gun_temp_fault_state, wg_temp_fault_state, buncher_temp_fault_state,
                 sol01_temp_fault_state, sol02_temp_fault_state])

# BPM01 threshold fault states - there is one FaultState for each DeviceState,
# there are 24 of them (8 for X, 8 for Y and 8 for TMIT).
#bpm01_fault_states=[]
bpm01_x_fault_states=[]
for i in range(0,2):
  bpm01_x_fault_state = models.FaultState(fault = bpm01_x_fault, device_state = bpm_x_states[i])
  session.add(bpm01_x_fault_state)
  bpm01_x_fault_states.append(bpm01_x_fault_state)
bpm01_y_fault_states=[]
for i in range(0,3):
  bpm01_y_fault_state = models.FaultState(fault = bpm01_y_fault, device_state = bpm_y_states[i])
  session.add(bpm01_y_fault_state)
  bpm01_y_fault_states.append(bpm01_y_fault_state)
bpm01_t_fault_states=[]
for i in range(0,4):
  bpm01_t_fault_state = models.FaultState(fault = bpm01_t_fault, device_state = bpm_t_states[i])
  session.add(bpm01_t_fault_state)
  bpm01_t_fault_states.append(bpm01_t_fault_state)

# BPM02 threshold fault states - there is one FaultState for each DeviceState,
# there are 24 of them (8 for X, 8 for Y and 8 for TMIT).
bpm02_x_fault_states=[]
for i in range(0,5):
  bpm02_x_fault_state = models.FaultState(fault = bpm02_x_fault, device_state = bpm_x_states[i])
  session.add(bpm02_x_fault_state)
  bpm02_x_fault_states.append(bpm02_x_fault_state)
bpm02_y_fault_states=[]
for i in range(0,6):
  bpm02_y_fault_state = models.FaultState(fault = bpm02_y_fault, device_state = bpm_y_states[i])
  session.add(bpm02_y_fault_state)
  bpm02_y_fault_states.append(bpm02_y_fault_state)
bpm02_t_fault_states=[]
for i in range(0,7):
  bpm02_t_fault_state = models.FaultState(fault = bpm02_t_fault, device_state = bpm_t_states[i])
  session.add(bpm02_t_fault_state)
  bpm02_t_fault_states.append(bpm02_t_fault_state)

# IM01 threshold fault states - there is one FaultState for each DeviceState,
# there are 32 of them (8 for INT1, 8 for INT2, 8 for INT3 and 8 for INT4).
im01_int1_fault_states=[]
for i in range(0,2):
  im01_int1_fault_state = models.FaultState(fault = im01_int1_fault, device_state = im_int1_states[i])
  session.add(im01_int1_fault_state)
  im01_int1_fault_states.append(im01_int1_fault_state)
im01_int2_fault_states=[]
for i in range(0,2):
  im01_int2_fault_state = models.FaultState(fault = im01_int2_fault, device_state = im_int2_states[i])
  session.add(im01_int2_fault_state)
  im01_int2_fault_states.append(im01_int2_fault_state)
im01_int3_fault_states=[]
for i in range(0,2):
  im01_int3_fault_state = models.FaultState(fault = im01_int3_fault, device_state = im_int3_states[i])
  session.add(im01_int3_fault_state)
  im01_int3_fault_states.append(im01_int3_fault_state)
im01_int4_fault_states=[]
for i in range(0,2):
  im01_int4_fault_state = models.FaultState(fault = im01_int4_fault, device_state = im_int4_states[i])
  session.add(im01_int4_fault_state)
  im01_int4_fault_states.append(im01_int4_fault_state)

# SOL1, SOL2, FC fault states
sol1_int1_fault_states=[]
sol2_int1_fault_states=[]
fc_int1_fault_states=[]
for i in range(0,2):
  sol1_int1_fault_state = models.FaultState(fault = sol1_int1_fault, device_state = sol1_int1_states[i])
  session.add(sol1_int1_fault_state)
  sol1_int1_fault_states.append(sol1_int1_fault_state)

  sol2_int1_fault_state = models.FaultState(fault = sol2_int1_fault, device_state = sol2_int1_states[i])
  session.add(sol2_int1_fault_state)
  sol2_int1_fault_states.append(sol2_int1_fault_state)

  fc_int1_fault_state = models.FaultState(fault = fc_int1_fault, device_state = fc_int1_states[i])
  session.add(fc_int1_fault_state)
  fc_int1_fault_states.append(fc_int1_fault_state)


# Fault states allowed beam classes.
yag_fault_in.add_allowed_class(beam_class=class_1, mitigation_device=aom)
yag_fault_moving.add_allowed_class(beam_class=class_0, mitigation_device=shutter)
yag_fault_broken.add_allowed_class(beam_class=class_0, mitigation_device=shutter)
gun_temp_fault_state.add_allowed_class(beam_class=class_0, mitigation_device=shutter)
wg_temp_fault_state.add_allowed_class(beam_class=class_0, mitigation_device=shutter)
buncher_temp_fault_state.add_allowed_class(beam_class=class_0, mitigation_device=shutter)
sol01_temp_fault_state.add_allowed_class(beam_class=class_0, mitigation_device=shutter)
sol02_temp_fault_state.add_allowed_class(beam_class=class_0, mitigation_device=shutter)
vvr1_fault_state.add_allowed_class(beam_class=class_0, mitigation_device=shutter)
vvr2_fault_state.add_allowed_class(beam_class=class_0, mitigation_device=shutter)

# Allowed beam classes for the BPM01/BPM02 FaultStates
for fault_state in bpm01_x_fault_states:
  fault_state.add_allowed_class(beam_class=class_0, mitigation_device=shutter)
  fault_state.add_allowed_class(beam_class=class_0, mitigation_device=aom)
for fault_state in bpm01_y_fault_states:
  fault_state.add_allowed_class(beam_class=class_0, mitigation_device=shutter)
  fault_state.add_allowed_class(beam_class=class_0, mitigation_device=aom)
for fault_state in bpm01_t_fault_states:
  fault_state.add_allowed_class(beam_class=class_0, mitigation_device=shutter)
  fault_state.add_allowed_class(beam_class=class_0, mitigation_device=aom)

for fault_state in bpm02_x_fault_states:
  fault_state.add_allowed_class(beam_class=class_0, mitigation_device=shutter)
  fault_state.add_allowed_class(beam_class=class_0, mitigation_device=aom)
for fault_state in bpm02_y_fault_states:
  fault_state.add_allowed_class(beam_class=class_0, mitigation_device=shutter)
  fault_state.add_allowed_class(beam_class=class_0, mitigation_device=aom)
for fault_state in bpm02_t_fault_states:
  fault_state.add_allowed_class(beam_class=class_0, mitigation_device=shutter)
  fault_state.add_allowed_class(beam_class=class_0, mitigation_device=aom)

for fault_state in im01_int1_fault_states:
  fault_state.add_allowed_class(beam_class=class_0, mitigation_device=shutter)
  fault_state.add_allowed_class(beam_class=class_0, mitigation_device=aom)
for fault_state in im01_int2_fault_states:
  fault_state.add_allowed_class(beam_class=class_0, mitigation_device=shutter)
  fault_state.add_allowed_class(beam_class=class_0, mitigation_device=aom)
for fault_state in im01_int3_fault_states:
  fault_state.add_allowed_class(beam_class=class_0, mitigation_device=shutter)
  fault_state.add_allowed_class(beam_class=class_0, mitigation_device=aom)
for fault_state in im01_int4_fault_states:
  fault_state.add_allowed_class(beam_class=class_0, mitigation_device=shutter)
  fault_state.add_allowed_class(beam_class=class_0, mitigation_device=aom)

for fault_state in sol1_int1_fault_states:
  fault_state.add_allowed_class(beam_class=class_0, mitigation_device=shutter)
  fault_state.add_allowed_class(beam_class=class_0, mitigation_device=aom)

for fault_state in sol2_int1_fault_states:
  fault_state.add_allowed_class(beam_class=class_0, mitigation_device=shutter)
  fault_state.add_allowed_class(beam_class=class_0, mitigation_device=aom)

for fault_state in fc_int1_fault_states:
  fault_state.add_allowed_class(beam_class=class_0, mitigation_device=shutter)
  fault_state.add_allowed_class(beam_class=class_0, mitigation_device=aom)

# Ignore logic
# 1) If YAG01 is IN, ignore SOL01 Current and SOL02 Current faults, VVR01 and VVR02 faults
yag01_in_condition = models.Condition(name="YAG01_IN", description="YAG01 screen IN", value=0)
session.add(yag01_in_condition)

yag01_condition_input = models.ConditionInput(bit_position=0,fault_state=yag_fault_in,
                                              condition=yag01_in_condition)
session.add(yag01_condition_input)

#sol01_ignore_condition = models.IgnoreCondition(condition=yag01_in_condition, fault_state=sol01_curr_fault_state)
#sol02_ignore_condition = models.IgnoreCondition(condition=yag01_in_condition, fault_state=sol02_curr_fault_state)
vvr1_condition = models.IgnoreCondition(condition=yag01_in_condition, fault_state=vvr1_fault_state)
vvr2_condition = models.IgnoreCondition(condition=yag01_in_condition, fault_state=vvr2_fault_state)
#session.add_all([sol01_ignore_condition, sol02_ignore_condition])
session.add_all([vvr1_condition, vvr2_condition])


session.commit()
