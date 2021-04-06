#!/usr/bin/env python
from mps_config import MPSConfig, models
from sqlalchemy import MetaData
from runtime_utils import RuntimeChecker

#
# Generate EIC database with only one threshold for the analog inputs
#

conf = MPSConfig()

#two_apps=True
two_apps=False

#Clear everything out of the database.
conf.clear_all()

#session is a connection to that database.
session = conf.session

#First lets define our mitigation devices.
linac = models.BeamDestination(name="Linac", description="Linac destination", destination_mask=0x01)
session.add(linac)

aom_destination = models.BeamDestination(name="AOM", description="AOM", destination_mask=0x02)
session.add(aom_destination)

#Make some beam classes.
# integration_window in units of 1uS
# min_period in units of 1uS
# total_charge in ?
#
# From the FDR:
#    Power class 0 = 0 rate (no beam)
#    Power class 1 = 10 Hz max rate, max charge = 300pC in 100mS
#    Power class 2 = Unlimited rate, max charge = 300uC in 1 second
#
# Min period: ~1uS * (value + 1)
#    if value=0, min period is 1uS
class_0 = models.BeamClass(number=0,name="PC0",description="No Beam",
                           integration_window=10, total_charge=0, min_period=0)
class_1 = models.BeamClass(number=1,name="PC1",description="YAG Max Power",
                           integration_window=91000, total_charge=300, min_period=91000)
class_2 = models.BeamClass(number=2,name="PC2",description="Full Power",
                           integration_window=910000, total_charge=300000, min_period=0)
session.add_all([class_0, class_1, class_2])

# EIC Link Node - L2KA00-05 (Level 17)
# Make a crate for BPMs, and for the mitigation LN
crate = models.Crate(crate_id=1, shelf_number=1, num_slots=8, location="L2KA00", rack="05", elevation=17, sector="LI00")
session.add_all([crate])

link_node = models.LinkNode(area="gunb", location="mp01", cpu="cpu-gunb0-mp01", crate=crate)
session.add(link_node)

#Define a mixed-mode link node (One digital AMC, one analog for IM01/SOL01-02 Curr/Faraday Cup Curr)
eic_digital_app = models.ApplicationType(name="Digital Card", number=0,
                                         digital_channel_count=32, digital_channel_size=1,
                                         digital_out_channel_count=2, digital_out_channel_size=1,
                                         analog_channel_count=0, analog_channel_size=1)
eic_analog_app = models.ApplicationType(name="AMC Analog Card", number=2,
                                        digital_channel_count=0, digital_channel_size=1,
                                        digital_out_channel_count=0, digital_out_channel_size=0,
                                        analog_channel_count=3, analog_channel_size=1)
session.add_all([eic_digital_app, eic_analog_app])

if not two_apps:
  eic_bpm_app = models.ApplicationType(name="BPM Card", number=1,
                                       digital_channel_count=0, digital_channel_size=1,
                                        digital_out_channel_count=0, digital_out_channel_size=0,
                                       analog_channel_count=2, analog_channel_size=1)
  eic_bcm_app = models.ApplicationType(name="BCM Analog Card", number=3,
                                       digital_channel_count=0, digital_channel_size=1,
                                       digital_out_channel_count=0, digital_out_channel_size=0,
                                       analog_channel_count=2, analog_channel_size=1)

  session.add_all([eic_bpm_app, eic_bcm_app])

# Application Cards (one for digital inputs, three for analog inputs)
link_node_card = models.ApplicationCard(name="EIC Digital Card", number=100, area="GUNB",
                                        type=eic_digital_app, slot_number=2, amc=2, #amc=2 -> RTM
                                        global_id=2, description="EIC Digital Input/Output", link_node=link_node)
sol_card = models.ApplicationCard(name="EIC Analog Inputs", number=104, area="GUNB",
                                  type=eic_analog_app, slot_number=2, amc=1,
                                  global_id=1, description="EIC Analog Inputs", link_node=link_node)

if not two_apps:
  bpm_card = models.ApplicationCard(name="EIC BPM1B/BPM2B", number=101, area="GUNB", 
                                    type=eic_bpm_app, slot_number=3,
                                    global_id=3, description="EIC BPM Status", link_node=link_node)
  im_card = models.ApplicationCard(name="EIC IM01B", number=102, area="GUNB",
                                   type=eic_bcm_app, slot_number=7,
                                   global_id=6, description="EIC IM Status", link_node=link_node)
  fc_card = models.ApplicationCard(name="EIC FC01", number=103, area="GUNB",
                                   type=eic_bcm_app, slot_number=6,
                                   global_id=5, description="EIC Faraday Cup Status", link_node=link_node)

crate.cards.append(link_node_card)
crate.cards.append(sol_card)
session.add_all([link_node_card, sol_card])

if not two_apps:
  crate.cards.append(bpm_card)
  crate.cards.append(im_card)
  crate.cards.append(fc_card)

  session.add_all([bpm_card, im_card, fc_card])


#
# According to WD-376-040-00-C0:
#
# Chan | Signal
# -----+----------------
#   0  | YAG01B IN
#   1  | YAG01B OUT
#   2  | SOL1B+return TEMP
#   3  | SOL2B+return TEMP
#   4  | SOL1B/2 FLOW
#   5  | BUNCHER TEMP (added 02/13/2019)
#   6  | BUNCHER FLOW (added 02/13/2019)
#   7  | VVR01 STATUS
#   8  | VVR02 STATUS
#   9  | MECH SHUTTER OPEN STATUS
#  10  | MECH SHUTTER CLOSED STATUS
#
#  21  | VVMG:LLOK:100:2 (MANUAL VALVE) STATUS
#
#  23  | GUN TEMP (added 02/13/2019)
#  24  | GUN FLOW (added 02/13/2019)
#  25  | FARADAY CUP TEMP STATUS
#  26  | GUN WAVEGUIDE TEMP STATUS
#  27  | FARADAY CUP FLOW (added 02/27/2019)
#  
digital_chans = []

names=[]
#===========  device,           zero name,    one name, fault state, channel number
names.append(("IN_LMTSW",       "NOT_IN",     "IS_IN",   0,  0)) # YAG01B IN
names.append(("OUT_LMTSW",      "NOT_OUT",    "IS_OUT",  0,  1)) # YAG01B OUT
names.append(("TEMP_SUM",       "IS_FAULTED", "IS_OK",   0,  2)) # SOL1B TEMP
names.append(("TEMP_SUM",       "IS_FAULTED", "IS_OK",   0,  3)) # SOL2B TEMP
names.append(("FLOW_SW",        "IS_FAULTED", "IS_OK",   0,  4)) # SOL1B/02 FLOW
names.append(("TEMP_SUM",       "IS_FAULTED", "IS_OK",   0,  5)) # BUNCHER TEMP
names.append(("FLOW_SW",        "IS_FAULTED", "IS_OK",   0,  6)) # BUNCHER FLOW
names.append(("STATUS",         "IS_FAULTED", "IS_OK",   0,  7)) # VVR01 STATUS
names.append(("STATUS",         "IS_FAULTED", "IS_OK",   0,  8)) # VVR02 STATUS
names.append(("OPEN_STATUS",    "NOT_OPEN",   "OPEN",    0,  9)) # Mechanical Shutter OPEN Status
names.append(("CLOSED_STATUS",  "NOT_CLOSED", "CLOSED",  0, 10)) # Mechanical Shutter CLOSE Status
names.append(("TEMPBD_SUM",     "IS_FAULTED", "IS_OK",   0, 23)) # GUN TEMP
names.append(("FLOW_SW",        "IS_FAULTED", "IS_OK",   0, 24)) # GUN FLOW
names.append(("STATUS",         "IS_FAULTED", "IS_OK",   0, 21)) # VVMG:LLOK:500:2
names.append(("TEMP_SUM",       "IS_FAULTED", "IS_OK",   0, 25)) # FARC TEMP
names.append(("TEMPWG_SUM",     "IS_FAULTED", "IS_OK",   0, 26)) # GUN WAVEGUIDE TEMP
names.append(("FLOW_SW",        "IS_FAULTED", "IS_OK",   0, 27)) # FARC FLOW

for i in range(0,len(names)):
  (name, z_name, o_name, alarm_state,chan_number) = names[i]
  chan = models.DigitalChannel(number=chan_number)
  chan.name = name
  chan.z_name = z_name
  chan.o_name = o_name
  chan.alarm_state = alarm_state
  chan.card = link_node_card
  digital_chans.append(chan)
  session.add(chan)

# Add two digital outputs and mitigation devices
shutter_channel = models.DigitalOutChannel(name="SHUTTER_CTRL", number=0, card=link_node_card)
aom_channel = models.DigitalOutChannel(name="SHUTTER_CTRL", number=1, card=link_node_card)
session.add_all([shutter_channel, aom_channel])

shutter_device_type = models.DeviceType(name="SHUT", description="Mechanical Laser Shutter")
aom_device_type = models.DeviceType(name="AOM", description="AOM Laser Shutter")
session.add_all([shutter_device_type, aom_device_type])

shutter = models.MitigationDevice(name="MS", description="Mechanical Shutter", position=100, beam_destination=linac,
                                  digital_out_channel=shutter_channel, area="GUNB", card = link_node_card,
                                  device_type = shutter_device_type)
aom = models.MitigationDevice(name="AOM", description="AOM", position=100, beam_destination=aom_destination,
                              digital_out_channel=aom_channel, area="GUNB", card = link_node_card,
                              device_type = aom_device_type)
session.add_all([shutter, aom])


sol01_channel = models.AnalogChannel(name="SOL1B Current", number=0, card = sol_card)
sol02_channel = models.AnalogChannel(name="SOL2B Current", number=1, card = sol_card)
session.add_all([sol01_channel, sol02_channel])

if not two_apps:
  im01_channel = models.AnalogChannel(name="IM01B Charge", number=0, card = im_card)
  fc_channel = models.AnalogChannel(name="Faraday Cup Current", number=0, card = fc_card)
  bpm01_channel = models.AnalogChannel(name="BPM1B", number=0, card = bpm_card)
  bpm02_channel = models.AnalogChannel(name="BPM2B", number=1, card = bpm_card)

  session.add_all([im01_channel, fc_channel,
                   bpm01_channel, bpm02_channel])

# Add digital device types
profmon_device_type = models.DeviceType(name="PROF", description="Profile Monitor")
temp_device_type = models.DeviceType(name="TEMP", description="Temperature Status")
flow_device_type = models.DeviceType(name="FLOW", description="Waterflow Status")
gun_device_type = models.DeviceType(name="GUN", description="Gun Device")
buncher_device_type = models.DeviceType(name="ACCL", description="Buncher")
vvr_device_type = models.DeviceType(name="VVPG", description="Vacuum Valve Pneumatic Status")
vvmg_device_type = models.DeviceType(name="VVMG", description="Manual Vacuum Valve Status")
shutter_status_device_type = models.DeviceType(name="SHUT", description="Laser Shutter Status")
session.add_all([profmon_device_type, temp_device_type, flow_device_type, vvr_device_type,
                 buncher_device_type, gun_device_type, shutter_status_device_type])

# Add analog device types
sol_curr_device_type = models.DeviceType(name="SOLN", description="Solenoid", num_integrators=1)
session.add(sol_curr_device_type)

fc_device_type = models.DeviceType(name="FARC", description="Faraday Cup", num_integrators=1)
session.add(fc_device_type)

if not two_apps:
  im_device_type = models.DeviceType(name="TORO", description="Toroid", num_integrators=2)
  session.add(im_device_type)

  bpm_device_type = models.DeviceType(name="BPMS", description="Beam Position Monitor", num_integrators=3)
  session.add(bpm_device_type)

# Define some states for the device types
# out sw bit 0
# in sw bit 1
screen_out        = models.DeviceState(name="OUT", description="Screen Out", device_type = profmon_device_type, value = 1)
screen_in         = models.DeviceState(name="IN", description="Screen In", device_type = profmon_device_type, value = 2)
screen_moving     = models.DeviceState(name="MOVING", description="Screen Moving", device_type = profmon_device_type, value = 0)
screen_broken     = models.DeviceState(name="BROKEN", description="Screen Broken", device_type = profmon_device_type, value = 3)

temp_device_fault = models.DeviceState(name="FAULT", description="Temperature Fault", device_type = temp_device_type, value = 0)
temp_device_ok    = models.DeviceState(name="OK", description="Temperature Ok", device_type = temp_device_type, value = 1)
flow_device_fault = models.DeviceState(name="FAULT", description="Flow Fault", device_type = flow_device_type, value = 0)
flow_device_ok    = models.DeviceState(name="OK", description="Flow Ok", device_type = flow_device_type, value = 1)
vvr_device_fault  = models.DeviceState(name="CLOSED", description="Vacuum Fault", device_type = vvr_device_type, value = 0)
vvr_device_ok     = models.DeviceState(name="OPENED", description="Vacuum Ok", device_type = vvr_device_type, value = 1)
vvmg_device_fault = models.DeviceState(name="CLOSED", description="Manual Vacuum Fault", device_type = vvmg_device_type, value = 0)
vvmg_device_ok    = models.DeviceState(name="OPENED", description="Manual Vacuum Ok",  device_type = vvmg_device_type, value = 1)

session.add_all([screen_out, screen_in, screen_moving, screen_broken,
                 temp_device_fault, temp_device_ok,
                 flow_device_fault, flow_device_ok,
                 vvr_device_fault, vvr_device_ok,
                 vvmg_device_fault, vvmg_device_ok])

# open bit 0
# close bit 1
# bit 1 | bit 0 | State
# ------+-------+------
#   0   |   1   | Open (value=1)
#   1   |   0   | Close (value=2)
#   0   |   0   | Moving (value=0)
#   1   |   1   | Broken (value=3)
# 
shutter_moving = models.DeviceState(name="MOVING", description="Shutter Moving", device_type = shutter_status_device_type, value = 0)
shutter_open   = models.DeviceState(name="OPENED", description="Shutter Opened",device_type = shutter_status_device_type, value = 1)
shutter_close  = models.DeviceState(name="CLOSED", description="Shutter Closed",device_type = shutter_status_device_type, value = 2)
shutter_broken = models.DeviceState(name="BROKEN", description="Shutter Broken",device_type = shutter_status_device_type, value = 3)

session.add_all([shutter_open, shutter_close, shutter_moving, shutter_broken])

#
# BPM DeviceStates - Threshold States
#
# There are 8 comparators for each X, Y and TMIT. Each comparator checks if
# the measurement in within the low and high thresholds. If a bit is set
# it means the measured value is outside the low/high window.
#
# Only 4 of the 8 thresholds are used for BPM01/BPM02, but they are all added
#
if not two_apps:
  bpm_x_states=[]
  bpm_y_states=[]
  bpm_t_states=[]
  state_value = 1
  # TMIT Thresholds - bits 0 through 7
  for i in range(0,8):
    state_name = "TMIT_T" + str(i) #+ "_FAULT"
    description = "TMIT Threshold" + str(i)
    if (i < 1):
      bpm_threshold_state = models.DeviceState(name=state_name, description=description,
                                               value=state_value, mask=state_value, device_type = bpm_device_type)
      bpm_t_states.append(bpm_threshold_state)
      session.add(bpm_threshold_state)
    state_value = (state_value << 1)
  # X Thresholds - bits 8 through 15
  for i in range(0,8):
    state_name = "X_T" + str(i) #+ "_FAULT"
    description = "X Threshold" + str(i)
    if (i < 1):
      bpm_threshold_state = models.DeviceState(name=state_name, description=description,
                                               value=state_value, mask=state_value, device_type = bpm_device_type)
      bpm_x_states.append(bpm_threshold_state)
      session.add(bpm_threshold_state)
    state_value = (state_value << 1)
  # Y Thresholds - bits 16 though 23
  for i in range(0,8):
    state_name = "Y_T" + str(i) #+ "_FAULT"
    description = "Y Threshold" + str(i)
    if (i < 1):
      bpm_threshold_state = models.DeviceState(name=state_name, description=description,
                                               value=state_value, mask=state_value, device_type = bpm_device_type)
      bpm_y_states.append(bpm_threshold_state)
      session.add(bpm_threshold_state)
    state_value = (state_value << 1)

session.commit()

# Other device states for analog devices, they are all grouped here.
# Defining two comparators for each of the four integrators for IM01
# Only two comparators for the first integrator for devices SOL1B, SOL2B and FC

im_charge_states=[] # Integrator #0 
im_diff_states=[] # Integrator #1
sol1_int1_states=[]
sol2_int1_states=[]
fc_int1_states=[]

state_value = 1
# Integrator #1 - bits 0 through 7
for i in range(0,8):
  if (i < 1):
    state_name = "I0_T" + str(i)# + "_FAULT"
    im_state_name = "CHARGE"
    if not two_apps:
      im_state = models.DeviceState(name=im_state_name, value=state_value, mask=state_value,
                                    device_type = im_device_type, description="Toroid Charge")
      fc_int1_state = models.DeviceState(name=im_state_name, value=state_value, mask=state_value,
                                         device_type = fc_device_type, description="FC Integrator 1")

    sol1_int1_state = models.DeviceState(name=state_name, value=state_value, mask=state_value, 
                                         device_type = sol_curr_device_type, description="SOL1B Integrator 1")
    sol2_int1_state = models.DeviceState(name=state_name, value=state_value, mask=state_value, 
                                         device_type = sol_curr_device_type, description="SOL2B Integrator 1")

    if (i < 1):
      sol1_int1_states.append(sol1_int1_state)
      sol2_int1_states.append(sol2_int1_state)
      if not two_apps:
        fc_int1_states.append(fc_int1_state)
        im_charge_states.append(im_state)

    session.add(sol1_int1_state)
    session.add(sol2_int1_state)

    if not two_apps:
      session.add(im_state)
      session.add(fc_int1_state)

  state_value = (state_value << 1)

# Integrator #2 - bits 8 through 15
for i in range(0,8):
  im_state_name = "DIFF"
  if (i < 1):
    if not two_apps:
      im_state = models.DeviceState(name=im_state_name, value=state_value,
                                    mask=state_value, device_type = im_device_type,
                                    description="Toroid Charge Difference")
      if (i < 1):
        im_diff_states.append(im_state)
    if not two_apps:
      session.add(im_state)
  state_value = (state_value << 1)

# Integrator #3 - bits 16 though 23
for i in range(0,8):
  state_name = "I2_T" + str(i)
  state_value = (state_value << 1)

# Integrator #4 - bits 24 though 32
for i in range(0,8):
  state_name = "I3_T" + str(i)
  state_value = (state_value << 1)

session.commit()

#Add digital devices
screen = models.DigitalDevice(name="YAG01B", position=753, z_location=-28, description="YAG01B Screen",
                              device_type = profmon_device_type, card = link_node_card, area="GUNB")
fc_temp = models.DigitalDevice(name="Faraday Cup Temperature", device_type = temp_device_type,
                               card = link_node_card, position = 999, z_location=-20,
                               description = "Faraday Cup Temperature Summary Input", area="GUNB",
                               measured_device_type_id = fc_device_type.id, evaluation=1)
sol01_temp = models.DigitalDevice(name="SOL1B Temp", position=212, z_location=-32, description="SOL1B Temperature",
                                  device_type = temp_device_type, card = link_node_card, area="GUNB",
                                  measured_device_type_id = sol_curr_device_type.id, evaluation=1)
sol02_temp = models.DigitalDevice(name="SOL2B Temp", position=823, z_location=-27,  description="SOL2B Temperature",
                                  device_type = temp_device_type, card = link_node_card, area="GUNB",
                                  measured_device_type_id = sol_curr_device_type.id, evaluation=1)
sol_flow = models.DigitalDevice(name="SOL1B/SOL2B Flow", position=212, z_location=-32, description="SOL1B and SOL2B Waterflow Status",
                                  device_type = flow_device_type, card = link_node_card, area="GUNB",
                                  measured_device_type_id = sol_curr_device_type.id, evaluation=1)
buncher_temp = models.DigitalDevice(name="Buncher Temp", position=455, z_location=-35,  description="Buncher Temperature",
                                  device_type = temp_device_type, card = link_node_card, area="GUNB",
                                  measured_device_type_id = buncher_device_type.id, evaluation=1)
buncher_flow = models.DigitalDevice(name="Buncher Flow", position=455, z_location=-35, description="Buncher Flow",
                                  device_type = flow_device_type, card = link_node_card, area="GUNB",
                                  measured_device_type_id = buncher_device_type.id, evaluation=1)
vvr1 = models.DigitalDevice(name="VVR01", position=100, z_location=-35, description="Vacuum Gate Valve VVR01",
                            device_type = vvr_device_type, card = link_node_card, area="GUNB", evaluation=1)
vvr2 = models.DigitalDevice(name="VVR02", position=941, z_location=-35, description="Vacuum Gate Valve VVR02",
                            device_type = vvr_device_type, card = link_node_card, area="GUNB", evaluation=1)
shutter_status = models.DigitalDevice(name="Mech. Shutter", position=100, z_location=-35, description="Mechanical Shutter Status",
                                      device_type = shutter_status_device_type, card = link_node_card, area="GUNB")
gun_temp = models.DigitalDevice(name="Gun Temp", position=100, z_location=-36,  description="Gun Temperature",
                                device_type = temp_device_type, card = link_node_card, area="GUNB",
                                measured_device_type_id = gun_device_type.id, evaluation=1)
gun_flow = models.DigitalDevice(name="Gun Flow", position=100, z_location=-36, description="Gun Flow",
                                device_type = flow_device_type, card = link_node_card, area="GUNB",
                                measured_device_type_id = gun_device_type.id, evaluation=1)
vvmg1 = models.DigitalDevice(name="VVMG02", position=500, z_location=-35, description="Manual Vacuum Gate Valve VVMG02",
                            device_type = vvmg_device_type, card = link_node_card, area="LLOK", evaluation=1)
gunwg_temp = models.DigitalDevice(name="Gun Waveguide Temp", position=100, z_location=-36,  description="Gun Waveguide Temperature",
                                  device_type = temp_device_type, card = link_node_card, area="GUNB",
                                  measured_device_type_id = gun_device_type.id, evaluation=1)
fc_flow = models.DigitalDevice(name="Faraday Cup Flow", position=999, z_location=-20,
                               description="Faraday Cup Flow",
                               device_type = flow_device_type, card = link_node_card, area="GUNB",
                               measured_device_type_id = fc_device_type.id, evaluation=1)

session.add_all([screen, fc_temp,
                 sol01_temp, sol02_temp, sol_flow,
                 buncher_temp, buncher_flow,
                 vvr1, vvr2,
                 gun_temp, gun_flow, fc_flow,
                 vvmg1, gunwg_temp])
session.add(shutter_status)

# Add analog devices
sol01 = models.AnalogDevice(name="SOL1B", device_type=sol_curr_device_type, channel=sol01_channel,
                            card=sol_card, position=212, description="SOL1B Current", evaluation=1, area="GUNB")
sol02 = models.AnalogDevice(name="SOL2B", device_type=sol_curr_device_type, channel=sol02_channel,
                            card=sol_card, position=823, description="SOL2B Current", evaluation=1, area="GUNB")
session.add_all([sol01, sol02])

if not two_apps:
  bpm01 = models.AnalogDevice(name="BPM1B", device_type = bpm_device_type, channel=bpm01_channel,
                              card = bpm_card, position=314, description="BPM1B", evaluation=1, area="GUNB")
  bpm02 = models.AnalogDevice(name="BPM2B", device_type = bpm_device_type, channel=bpm02_channel,
                              card =bpm_card, position=925, description="BPM2B", evaluation=1, area="GUNB")
  im01 = models.AnalogDevice(name="IM01B", device_type=im_device_type, channel=im01_channel,
                             card=im_card, position=360, description="Toroid, ICT Charge", evaluation=1, area="GUNB")
  fc = models.AnalogDevice(name="FCDG0DU", device_type=fc_device_type, channel=fc_channel,
                             card=fc_card, position=999, description="Faraday Cup Current", evaluation=1, area="GUNB")
  session.add_all([bpm01, bpm02, im01, fc])

# Give the device some inputs.  It has in and out limit switches.
yag_in_lim_sw = models.DeviceInput(channel = digital_chans[0], bit_position = 1, digital_device = screen, fault_value=1)
yag_out_lim_sw = models.DeviceInput(channel = digital_chans[1], bit_position = 0, digital_device = screen, fault_value=1)
sol01_temp_channel = models.DeviceInput(channel = digital_chans[2], bit_position = 0,
                                        digital_device = sol01_temp, fault_value=0)
sol02_temp_channel = models.DeviceInput(channel = digital_chans[3], bit_position = 0,
                                        digital_device = sol02_temp, fault_value=0)
sol_flow_channel = models.DeviceInput(channel = digital_chans[4], bit_position = 0,
                                      digital_device = sol_flow, fault_value=0)
buncher_temp_channel = models.DeviceInput(channel = digital_chans[5], bit_position = 0,
                                          digital_device = buncher_temp, fault_value=0)
buncher_flow_channel = models.DeviceInput(channel = digital_chans[6], bit_position = 0,
                                          digital_device = buncher_flow, fault_value=0)
vvr1_channel =  models.DeviceInput(channel = digital_chans[7], bit_position = 0,
                                   digital_device = vvr1, fault_value=0)
vvr2_channel =  models.DeviceInput(channel = digital_chans[8], bit_position = 0,
                                   digital_device = vvr2, fault_value=0)
shutter_open_sw = models.DeviceInput(channel = digital_chans[9], bit_position=0,
                                     digital_device=shutter_status, fault_value=0)
shutter_close_sw = models.DeviceInput(channel = digital_chans[10], bit_position=1,
                                      digital_device=shutter_status, fault_value=1)
gun_temp_channel = models.DeviceInput(channel = digital_chans[11], bit_position = 0,
                                      digital_device = gun_temp, fault_value=0)
gun_flow_channel = models.DeviceInput(channel = digital_chans[12], bit_position = 0,
                                      digital_device = gun_flow, fault_value=0)
vvmg1_channel =  models.DeviceInput(channel = digital_chans[13], bit_position = 0,
                                    digital_device = vvmg1, fault_value=0)
fc_temp_channel = models.DeviceInput(channel = digital_chans[14], bit_position = 0,
                                     digital_device = fc_temp, fault_value=0)
gunwg_temp_channel = models.DeviceInput(channel = digital_chans[15], bit_position = 0,
                                      digital_device = gunwg_temp, fault_value=0)
fc_flow_channel = models.DeviceInput(channel = digital_chans[16], bit_position = 0,
                                     digital_device = fc_flow, fault_value=0)
session.add_all([yag_out_lim_sw,yag_in_lim_sw,
                 sol01_temp_channel, sol02_temp_channel,
                 buncher_temp_channel, buncher_flow_channel,
                 fc_temp, sol_flow_channel,
                 shutter_open_sw, shutter_close_sw,
                 gun_temp_channel, gun_flow_channel, gunwg_temp_channel,
                 vvr1_channel, vvr2_channel, vvmg1_channel])

#Configure faults for the digital devices
yag_fault = models.Fault(name="TGT", description="YAG01B Profile Monitor Screen Fault")
fc_temp_fault = models.Fault(name="TEMP_SUM", description="Faraday Cup Temperature Fault")
sol01_temp_fault = models.Fault(name="TEMP_SUM", description="SOL1B Temperature Fault")
sol02_temp_fault = models.Fault(name="TEMP_SUM", description="SOL2B Temperature Fault")
sol_flow_fault = models.Fault(name="FLOW_SW", description="SOL1B/SOL2B Waterflow Fault")
buncher_temp_fault = models.Fault(name="TEMP_SUM", description="Buncher Temperature Fault")
buncher_flow_fault = models.Fault(name="FLOW_SW", description="Buncher Waterflow Fault")
vvr1_fault = models.Fault(name="VVR01", description="VVR01 Vacuum Valve Fault")
vvr2_fault = models.Fault(name="VVR02", description="VVR02 Vacuum Valve Fault")
gun_temp_fault = models.Fault(name="TEMPBD_SUM", description="Gun Temperature Fault")
gun_flow_fault = models.Fault(name="FLOW_SW", description="Gun Waterflow Fault")
vvmg1_fault = models.Fault(name="VVMG2", description="VVMG:LLOK:500:2 Man. Vac. Valve Fault")
gunwg_temp_fault = models.Fault(name="TEMPWG_SUM", description="Gun Waveguide Temperature Fault")
fc_flow_fault = models.Fault(name="FLOW_SW", description="Faraday Cup Waterflow Fault")
session.add_all([yag_fault,  sol01_temp_fault, sol02_temp_fault, fc_temp_fault])
session.add_all([vvr1_fault, vvr2_fault, vvmg1_fault])
session.add_all([sol_flow_fault, fc_flow_fault])
session.add_all([buncher_temp_fault, buncher_flow_fault, 
                 gun_temp_fault, gun_flow_fault, gunwg_temp_fault])
shutter_fault = models.Fault(name="SHUT", description="Mechanical Shutter Status Fault")
session.add(shutter_fault)

sol1_int1_fault = models.Fault(name="I0", description="SOL1B Integrator #0 Fault")
sol2_int1_fault = models.Fault(name="I0", description="SOL2B Integrator #0 Fault")
session.add_all([sol1_int1_fault, sol2_int1_fault])

if not two_apps: 
  bpm01_x_fault = models.Fault(name="X", description="BPM1B X Threshold Fault")
  bpm01_y_fault = models.Fault(name="Y", description="BPM1B Y Threshold Fault")
  bpm01_t_fault = models.Fault(name="TMIT", description="BPM1B TMIT Threshold Fault")
  session.add_all([bpm01_x_fault, bpm01_y_fault, bpm01_t_fault])

  bpm02_x_fault = models.Fault(name="X", description="BPM2B X Threshold Fault")
  bpm02_y_fault = models.Fault(name="Y", description="BPM2B Y Threshold Fault")
  bpm02_t_fault = models.Fault(name="TMIT", description="BPM2B TMIT Threshold Fault")
  session.add_all([bpm02_x_fault, bpm02_y_fault, bpm02_t_fault])

  im01_charge_fault = models.Fault(name="CHARGE", description="IM01B Charge Fault")
  im01_diff_fault = models.Fault(name="DIFF", description="IM01B/BPM1B Difference Fault")
  session.add_all([im01_charge_fault, im01_diff_fault])

  fc_int1_fault = models.Fault(name="CHARGE", description="FC01 Integrator #0 Fault")
  session.add_all([fc_int1_fault])

# Inputs for the digital faults
yag_fault_input = models.FaultInput(bit_position = 0, device = screen, fault = yag_fault)
fc_temp_fault_input = models.FaultInput(bit_position = 0, device = fc_temp, fault = fc_temp_fault)
sol01_temp_fault_input = models.FaultInput(bit_position = 0, device = sol01_temp, fault = sol01_temp_fault)
sol02_temp_fault_input = models.FaultInput(bit_position = 0, device = sol02_temp, fault = sol02_temp_fault)
sol_flow_fault_input = models.FaultInput(bit_position = 0, device = sol_flow, fault = sol_flow_fault)
buncher_temp_fault_input = models.FaultInput(bit_position = 0, device = buncher_temp, fault = buncher_temp_fault)
buncher_flow_fault_input = models.FaultInput(bit_position = 0, device = buncher_flow, fault = buncher_flow_fault)
vvr1_fault_input = models.FaultInput(bit_position = 0, device = vvr1, fault = vvr1_fault)
vvr2_fault_input = models.FaultInput(bit_position = 0, device = vvr2, fault = vvr2_fault)
gun_temp_fault_input = models.FaultInput(bit_position = 0, device = gun_temp, fault = gun_temp_fault)
gun_flow_fault_input = models.FaultInput(bit_position = 0, device = gun_flow, fault = gun_flow_fault)
gunwg_temp_fault_input = models.FaultInput(bit_position = 0, device = gunwg_temp, fault = gunwg_temp_fault)
fc_flow_fault_input = models.FaultInput(bit_position = 0, device = fc_flow, fault = fc_flow_fault)

session.add_all([yag_fault_input, fc_temp_fault_input, fc_flow_fault_input,
                 sol01_temp_fault_input, sol02_temp_fault_input,
                 buncher_temp_fault_input, buncher_flow_fault_input,
                 gun_temp_fault_input, gun_flow_fault_input, gunwg_temp_fault,
                 sol_flow_fault_input, vvr1_fault_input, vvr2_fault_input])

shutter_fault_input = models.FaultInput(bit_position = 0, device = shutter_status, fault = shutter_fault)
session.add(shutter_fault_input)

vvmg1_fault_input = models.FaultInput(bit_position = 0, device = vvmg1, fault = vvmg1_fault)
session.add(vvmg1_fault_input)

# The bit_position is the location within the fault (bpm01_x_fault) where
# the value from the device (bpm01) will go
sol1_int1_fault_input = models.FaultInput(bit_position = 0, device = sol01, fault = sol1_int1_fault)
sol2_int1_fault_input = models.FaultInput(bit_position = 0, device = sol02, fault = sol2_int1_fault)
session.add_all([sol1_int1_fault_input, sol2_int1_fault_input])

if not two_apps:
  bpm01_x_fault_input = models.FaultInput(bit_position = 0, device = bpm01, fault = bpm01_x_fault)
  bpm01_y_fault_input = models.FaultInput(bit_position = 0, device = bpm01, fault = bpm01_y_fault)
  bpm01_t_fault_input = models.FaultInput(bit_position = 0, device = bpm01, fault = bpm01_t_fault)

  bpm02_x_fault_input = models.FaultInput(bit_position = 0, device = bpm02, fault = bpm02_x_fault)
  bpm02_y_fault_input = models.FaultInput(bit_position = 0, device = bpm02, fault = bpm02_y_fault)
  bpm02_t_fault_input = models.FaultInput(bit_position = 0, device = bpm02, fault = bpm02_t_fault)
  session.add_all([bpm01_x_fault_input, bpm01_y_fault_input, bpm01_t_fault_input,
                   bpm02_x_fault_input, bpm02_y_fault_input, bpm02_t_fault_input])

  im01_charge_fault_input = models.FaultInput(bit_position = 0, device = im01, fault = im01_charge_fault)
  im01_diff_fault_input = models.FaultInput(bit_position = 0, device = im01, fault = im01_diff_fault)
  session.add_all([im01_charge_fault_input, im01_diff_fault_input])

  fc_int1_fault_input = models.FaultInput(bit_position = 0, device = fc, fault = fc_int1_fault)
  session.add_all([fc_int1_fault_input])

# FaultStates
yag_fault_in = models.FaultState(device_state = screen_in, fault = yag_fault)
yag_fault_moving = models.FaultState(fault = yag_fault, device_state = screen_moving)
yag_fault_broken = models.FaultState(fault = yag_fault, device_state = screen_broken)
fc_temp_fault_state = models.FaultState(fault = fc_temp_fault, device_state = temp_device_fault)
sol01_temp_fault_state = models.FaultState(fault = sol01_temp_fault, device_state = temp_device_fault)
sol02_temp_fault_state = models.FaultState(fault = sol02_temp_fault, device_state = temp_device_fault)
sol_flow_fault_state = models.FaultState(fault = sol_flow_fault, device_state = flow_device_fault)
buncher_temp_fault_state = models.FaultState(fault = buncher_temp_fault, device_state = temp_device_fault)
buncher_flow_fault_state = models.FaultState(fault = buncher_flow_fault, device_state = flow_device_fault)
vvr1_fault_state = models.FaultState(fault = vvr1_fault, device_state = vvr_device_fault)
vvr2_fault_state = models.FaultState(fault = vvr2_fault, device_state = vvr_device_fault)
gun_temp_fault_state = models.FaultState(fault = gun_temp_fault, device_state = temp_device_fault)
gun_flow_fault_state = models.FaultState(fault = gun_flow_fault, device_state = flow_device_fault)
gunwg_temp_fault_state = models.FaultState(fault = gunwg_temp_fault, device_state = temp_device_fault)
fc_flow_fault_state = models.FaultState(fault = fc_flow_fault, device_state = flow_device_fault)

session.add_all([yag_fault_in, yag_fault_moving, yag_fault_broken, fc_temp_fault_state,
                 fc_flow_fault_state,
                 buncher_temp_fault_state, buncher_flow_fault_state,
                 gun_temp_fault_state, gun_flow_fault_state, gunwg_temp_fault_state,
                 sol01_temp_fault_state, sol02_temp_fault_state, sol_flow_fault_state])

shutter_fault_broken = models.FaultState(fault = shutter_fault, device_state = shutter_broken)
session.add(shutter_fault_broken)

vvmg1_fault_state = models.FaultState(fault = vvmg1_fault, device_state = vvmg_device_fault)
session.add(vvmg1_fault_state)

# SOL1B, SOL2B fault states
sol1_int1_fault_states=[]
sol2_int1_fault_states=[]
for i in range(0,1):
  sol1_int1_fault_state = models.FaultState(fault = sol1_int1_fault, device_state = sol1_int1_states[i])
  session.add(sol1_int1_fault_state)
  sol1_int1_fault_states.append(sol1_int1_fault_state)

  sol2_int1_fault_state = models.FaultState(fault = sol2_int1_fault, device_state = sol2_int1_states[i])
  session.add(sol2_int1_fault_state)
  sol2_int1_fault_states.append(sol2_int1_fault_state)

if not two_apps:
  # BPM01 threshold fault states - there is one FaultState for each DeviceState,
  # there are 24 of them (8 for X, 8 for Y and 8 for TMIT).
  bpm01_x_fault_states=[]
  for i in range(0,1):
    bpm01_x_fault_state = models.FaultState(fault = bpm01_x_fault, device_state = bpm_x_states[i])
    session.add(bpm01_x_fault_state)
    bpm01_x_fault_states.append(bpm01_x_fault_state)
  bpm01_y_fault_states=[]
  for i in range(0,1):
    bpm01_y_fault_state = models.FaultState(fault = bpm01_y_fault, device_state = bpm_y_states[i])
    session.add(bpm01_y_fault_state)
    bpm01_y_fault_states.append(bpm01_y_fault_state)
  bpm01_t_fault_states=[]
  for i in range(0,1):
    bpm01_t_fault_state = models.FaultState(fault = bpm01_t_fault, device_state = bpm_t_states[i])
    session.add(bpm01_t_fault_state)
    bpm01_t_fault_states.append(bpm01_t_fault_state)

  # BPM02 threshold fault states - there is one FaultState for each DeviceState,
  # there are 24 of them (8 for X, 8 for Y and 8 for TMIT).
  bpm02_x_fault_states=[]
  for i in range(0,1):
    bpm02_x_fault_state = models.FaultState(fault = bpm02_x_fault, device_state = bpm_x_states[i])
    session.add(bpm02_x_fault_state)
    bpm02_x_fault_states.append(bpm02_x_fault_state)
  bpm02_y_fault_states=[]
  for i in range(0,1):
    bpm02_y_fault_state = models.FaultState(fault = bpm02_y_fault, device_state = bpm_y_states[i])
    session.add(bpm02_y_fault_state)
    bpm02_y_fault_states.append(bpm02_y_fault_state)
  bpm02_t_fault_states=[]
  for i in range(0,1):
    bpm02_t_fault_state = models.FaultState(fault = bpm02_t_fault, device_state = bpm_t_states[i])
    session.add(bpm02_t_fault_state)
    bpm02_t_fault_states.append(bpm02_t_fault_state)

  # IM01 threshold fault states - there is one FaultState for each DeviceState,
  # there are 32 of them (8 for INT1, 8 for INT2, 8 for INT3 and 8 for INT4).
  im01_charge_fault_states=[]
  for i in range(0,1):
    im01_charge_fault_state = models.FaultState(fault = im01_charge_fault, device_state = im_charge_states[i])
    session.add(im01_charge_fault_state)
    im01_charge_fault_states.append(im01_charge_fault_state)

  im01_diff_fault_states=[]
  for i in range(0,1):
    im01_diff_fault_state = models.FaultState(fault = im01_diff_fault, device_state = im_diff_states[i])
    session.add(im01_diff_fault_state)
    im01_diff_fault_states.append(im01_diff_fault_state)

  # FC fault states
  fc_int1_fault_states=[]
  for i in range(0,1):
    fc_int1_fault_state = models.FaultState(fault = fc_int1_fault, device_state = fc_int1_states[i])
    session.add(fc_int1_fault_state)
    fc_int1_fault_states.append(fc_int1_fault_state)


# Fault states allowed beam classes. (Linac destination)
yag_fault_in.add_allowed_class(beam_class=class_1, beam_destination=linac)
yag_fault_moving.add_allowed_class(beam_class=class_0, beam_destination=linac)
yag_fault_broken.add_allowed_class(beam_class=class_0, beam_destination=linac)
fc_temp_fault_state.add_allowed_class(beam_class=class_0, beam_destination=linac)
sol01_temp_fault_state.add_allowed_class(beam_class=class_0, beam_destination=linac)
sol02_temp_fault_state.add_allowed_class(beam_class=class_0, beam_destination=linac)
sol_flow_fault_state.add_allowed_class(beam_class=class_0, beam_destination=linac)
buncher_temp_fault_state.add_allowed_class(beam_class=class_0, beam_destination=linac)
buncher_flow_fault_state.add_allowed_class(beam_class=class_0, beam_destination=linac)
vvr1_fault_state.add_allowed_class(beam_class=class_0, beam_destination=linac)
vvr2_fault_state.add_allowed_class(beam_class=class_0, beam_destination=linac)
shutter_fault_broken.add_allowed_class(beam_class=class_0, beam_destination=linac)
gun_temp_fault_state.add_allowed_class(beam_class=class_0, beam_destination=linac)
gun_flow_fault_state.add_allowed_class(beam_class=class_0, beam_destination=linac)
vvmg1_fault_state.add_allowed_class(beam_class=class_0, beam_destination=linac)
gunwg_temp_fault_state.add_allowed_class(beam_class=class_0, beam_destination=linac)
fc_flow_fault_state.add_allowed_class(beam_class=class_0, beam_destination=linac)

# AOM Destination
yag_fault_in.add_allowed_class(beam_class=class_1, beam_destination=aom_destination)
yag_fault_moving.add_allowed_class(beam_class=class_0, beam_destination=aom_destination)
yag_fault_broken.add_allowed_class(beam_class=class_0, beam_destination=aom_destination)
fc_temp_fault_state.add_allowed_class(beam_class=class_0, beam_destination=aom_destination)
sol01_temp_fault_state.add_allowed_class(beam_class=class_0, beam_destination=aom_destination)
sol02_temp_fault_state.add_allowed_class(beam_class=class_0, beam_destination=aom_destination)
sol_flow_fault_state.add_allowed_class(beam_class=class_0, beam_destination=aom_destination)
buncher_temp_fault_state.add_allowed_class(beam_class=class_0, beam_destination=aom_destination)
buncher_flow_fault_state.add_allowed_class(beam_class=class_0, beam_destination=aom_destination)
vvr1_fault_state.add_allowed_class(beam_class=class_0, beam_destination=aom_destination)
vvr2_fault_state.add_allowed_class(beam_class=class_0, beam_destination=aom_destination)
shutter_fault_broken.add_allowed_class(beam_class=class_0, beam_destination=aom_destination)
gun_temp_fault_state.add_allowed_class(beam_class=class_0, beam_destination=aom_destination)
gun_flow_fault_state.add_allowed_class(beam_class=class_0, beam_destination=aom_destination)
vvmg1_fault_state.add_allowed_class(beam_class=class_0, beam_destination=aom_destination)
gunwg_temp_fault_state.add_allowed_class(beam_class=class_0, beam_destination=aom_destination)
fc_flow_fault_state.add_allowed_class(beam_class=class_0, beam_destination=aom_destination)


for fault_state in sol1_int1_fault_states:
  fault_state.add_allowed_class(beam_class=class_0, beam_destination=linac)
  fault_state.add_allowed_class(beam_class=class_0, beam_destination=aom_destination)

for fault_state in sol2_int1_fault_states:
  fault_state.add_allowed_class(beam_class=class_0, beam_destination=linac)
  fault_state.add_allowed_class(beam_class=class_0, beam_destination=aom_destination)

# Allowed beam classes for the BPM01/BPM02 FaultStates
if not two_apps:
  for fault_state in bpm01_x_fault_states:
    fault_state.add_allowed_class(beam_class=class_0, beam_destination=linac)
    fault_state.add_allowed_class(beam_class=class_0, beam_destination=aom_destination)
  for fault_state in bpm01_y_fault_states:
    fault_state.add_allowed_class(beam_class=class_0, beam_destination=linac)
    fault_state.add_allowed_class(beam_class=class_0, beam_destination=aom_destination)
  for fault_state in bpm01_t_fault_states:
    fault_state.add_allowed_class(beam_class=class_0, beam_destination=linac)
    fault_state.add_allowed_class(beam_class=class_0, beam_destination=aom_destination)

  for fault_state in bpm02_x_fault_states:
    fault_state.add_allowed_class(beam_class=class_0, beam_destination=linac)
    fault_state.add_allowed_class(beam_class=class_0, beam_destination=aom_destination)
  for fault_state in bpm02_y_fault_states:
    fault_state.add_allowed_class(beam_class=class_0, beam_destination=linac)
    fault_state.add_allowed_class(beam_class=class_0, beam_destination=aom_destination)
  for fault_state in bpm02_t_fault_states:
    fault_state.add_allowed_class(beam_class=class_0, beam_destination=linac)
    fault_state.add_allowed_class(beam_class=class_0, beam_destination=aom_destination)

  for fault_state in im01_charge_fault_states:
    fault_state.add_allowed_class(beam_class=class_0, beam_destination=linac)
    fault_state.add_allowed_class(beam_class=class_0, beam_destination=aom_destination)
  for fault_state in im01_diff_fault_states:
    fault_state.add_allowed_class(beam_class=class_0, beam_destination=linac)
    fault_state.add_allowed_class(beam_class=class_0, beam_destination=aom_destination)

  for fault_state in fc_int1_fault_states:
    fault_state.add_allowed_class(beam_class=class_0, beam_destination=linac)
    fault_state.add_allowed_class(beam_class=class_0, beam_destination=aom_destination)

# 1) If YAG01 is IN, ignore SOL2B current
# value=1 means the condition is met when the yag01_condition_input is faulted
yag01_in_condition = models.Condition(name="YAG01B_IN", description="YAG01B target screen IN", value=1)
session.add(yag01_in_condition)

yag01_condition_input = models.ConditionInput(bit_position=0,fault_state=yag_fault_in,
                                              condition=yag01_in_condition)
session.add(yag01_condition_input)

# Add SOL2B device to ignore condition
ignore_condition = models.IgnoreCondition(condition=yag01_in_condition, analog_device=sol02)
session.add(ignore_condition)

if not two_apps:
  # Add FARC device to ignore condition
  ignore_condition = models.IgnoreCondition(condition=yag01_in_condition, analog_device=fc)
  session.add(ignore_condition)

  # Add BPM2B device to ignore condition
  ignore_condition = models.IgnoreCondition(condition=yag01_in_condition, analog_device=bpm02)
  session.add(ignore_condition)

  # Add condition to ignore TORO DIFF - leaving TORO CHARGE enabled
  # This is a special EIC only case 
  ignore_condition = models.IgnoreCondition(condition=yag01_in_condition, 
                                            fault_state=im01_diff_fault_states[0],
                                            analog_device=im01)
  session.add(ignore_condition)


session.commit()

rt = RuntimeChecker(session, conf.runtime_session, False)
rt.create_runtime_database()
