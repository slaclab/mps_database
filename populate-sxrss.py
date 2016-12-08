from mps_config import MPSConfig, models
from sqlalchemy import MetaData

#
# SXRSS Logic Database
#
# Devices: M1, Slit (SL), M2, M3, ChicanePower (CP)
#
# Channels:
#  0 - M1 In
#  1 - M1 Out
#  2 - Slit In
#  3 - Slit Out
#  4 - M2 In
#  5 - M2 Out
#  6 - M3 In
#  7 - M3 Out
#  8 - ChicanePower
#
# Rules:
#
# +-----+-----+-----+-----+-----+--------+
# | M1  | SL  | M2  | M3  | CP  | Beam   |
# +-----+-----+-----+-----+-----+--------+
# | In  | Any | Any | In  | On  | 120 Hz |
# +-----+-----+-----+-----+-----+--------+
# | Out | In  | Out | Out | On  | 120 Hz |
# +-----+-----+-----+-----+-----+--------+
# | Out | Out | Out | Out | Any | 120 Hz |
# +-----+-----+-----+-----+-----+--------+
# * All other combinations go to 0 Hz
#
#


#The MPSConfig object points to our database file.
conf = MPSConfig('mps_sxrss.db')

#Clear everything out of the database.
conf.clear_all()

#session is a connection to that database.
session = conf.session

#First lets define our mitigation devices.
shutter = models.MitigationDevice(name="Shutter")
session.add(shutter)

#Make some beam classes.
class_0 = models.BeamClass(number=0,name="0 Hz")
class_1 = models.BeamClass(number=1,name="1 Hz")
class_2 = models.BeamClass(number=2,name="10 Hz")
class_3 = models.BeamClass(number=3,name="120 Hz")
session.add_all([class_0, class_1, class_2, class_3])

#Make a crate for LN with digital inputs
ln_crate = models.Crate(number=1, shelf_number=1, num_slots=6)
session.add(ln_crate)

#Make a crate for mitigation LN
mitigation_crate = models.Crate(number=2, shelf_number=1, num_slots=6)
session.add(mitigation_crate)

#Define a mixed-mode link node (One digital AMC only)
mixed_link_node_type = models.ApplicationType(name="Mixed Mode Link Node", number=0, digital_channel_count=9, digital_channel_size=1, analog_channel_count=0, analog_channel_size=1)

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
ln_crate.cards.append(link_node_card)
session.add(link_node_card)

# Channels:
#  0 - M1 In
#  1 - M1 Out
#  2 - Slit In
#  3 - Slit Out
#  4 - M2 In
#  5 - M2 Out
#  6 - M3 In
#  7 - M3 Out
#  8 - ChicanePower
digital_chans = []
chan_name = ['M1_IN_SWITCH', 'M1_OUT_SWITCH',
             'SL_IN_SWITCH', 'SL_OUT_SWITCH',
             'M2_IN_SWITCH', 'M2_OUT_SWITCH',
             'M3_IN_SWITCH', 'M3_OUT_SWITCH',
             'CHI_POWER']

for i in range(0,9):
  chan = models.DigitalChannel(number=i)
  chan.name =chan_name[i]
  chan.card = link_node_card
  digital_chans.append(chan)
  session.add(chan)

# Add device types
insertion_device_type = models.DeviceType(name="Insertion Device")
power_device_type = models.DeviceType(name="Power Device")
sxrss_device_type = models.DeviceType(name="SXRSS Protection Device")
session.add_all([insertion_device_type, power_device_type, sxrss_device_type])
session.commit()

# Define some states for the insertion device type
device_out = models.DeviceState(name="Out", device_type = insertion_device_type, value = 1)
device_in = models.DeviceState(name="In", device_type = insertion_device_type, value = 2)
device_moving = models.DeviceState(name="Moving", device_type = insertion_device_type, value = 0)
device_broken = models.DeviceState(name="Broken", device_type = insertion_device_type, value = 3)
power_on =  models.DeviceState(name="Power On", device_type = power_device_type, value = 1)
power_off =  models.DeviceState(name="Power Off", device_type = power_device_type, value = 1)

# Define states for SXRSS composite device
sxrss_default_state = models.DeviceState(name="SXRSS Faulted", value=0xFFFF, mask=0, device_type = sxrss_device_type)
sxrss_state_ss = models.DeviceState(name="SXRSS SS", value=0x141, mask=0x1C3, device_type = sxrss_device_type)
sxrss_state_harmonic = models.DeviceState(name="SXRSS Harmonic", value=0x1A6, device_type = sxrss_device_type)
sxrss_state_sase = models.DeviceState(name="SXRSS SASE", value=0xAA, mask=0xFF, device_type = sxrss_device_type)

session.add_all([device_out, device_in, device_moving, device_broken, power_on, power_off,
                 sxrss_default_state, sxrss_state_ss, sxrss_state_harmonic, sxrss_state_sase])

# add devices
m1_device = models.DigitalDevice(name="M1", z_position=30, description="M1 Insertion Device",
                                 device_type = insertion_device_type, application = global_app)
slit_device = models.DigitalDevice(name="SL", z_position=60, description="Slit Insertion Device",
                                   device_type = insertion_device_type, application = global_app)
m2_device = models.DigitalDevice(name="M2", z_position=70, description="M2 Insertion Device",
                                 device_type = insertion_device_type, application = global_app)
m3_device = models.DigitalDevice(name="M3", z_position=72, description="M3 Insertion Device",
                                 device_type = insertion_device_type, application = global_app)
cp_device = models.DigitalDevice(name="CP", z_position=10, description="Chicane Power Device",
                                 device_type = power_device_type, application = global_app)
session.add_all([m1_device, slit_device, m2_device, m3_device, cp_device])

# Assign inputs to devices
m1_in_sw = models.DeviceInput(channel = digital_chans[0], bit_position = 0, digital_device = m1_device)
m1_out_sw = models.DeviceInput(channel = digital_chans[1], bit_position = 1, digital_device = m1_device)
slit_in_sw = models.DeviceInput(channel = digital_chans[2], bit_position = 0, digital_device = slit_device)
slit_out_sw = models.DeviceInput(channel = digital_chans[3], bit_position = 1, digital_device = slit_device)
m2_in_sw = models.DeviceInput(channel = digital_chans[4], bit_position = 0, digital_device = m2_device)
m2_out_sw = models.DeviceInput(channel = digital_chans[5], bit_position = 1, digital_device = m2_device)
m3_in_sw = models.DeviceInput(channel = digital_chans[6], bit_position = 0, digital_device = m3_device)
m3_out_sw = models.DeviceInput(channel = digital_chans[7], bit_position = 1, digital_device = m3_device)
cp_channel = models.DeviceInput(channel = digital_chans[8], bit_position = 0, digital_device = cp_device)
session.add_all([m1_in_sw, m1_out_sw,
                 slit_in_sw, slit_out_sw,
                 m2_in_sw, m2_out_sw,
                 m3_in_sw, m3_out_sw, cp_channel])

# Configure faults for the device
sxrss_fault = models.Fault(name='SXRSS Fault')
session.add(sxrss_fault)

# Add fault inputs to SXRSS fault
m1_fault_input = models.FaultInput(bit_position=0, device=m1_device, fault=sxrss_fault)
slit_fault_input = models.FaultInput(bit_position=2, device=slit_device, fault=sxrss_fault)
m2_fault_input = models.FaultInput(bit_position=4, device=m2_device, fault=sxrss_fault)
m3_fault_input = models.FaultInput(bit_position=6, device=m3_device, fault=sxrss_fault)
cp_fault_input = models.FaultInput(bit_position=8, device=cp_device, fault=sxrss_fault)
session.add_all([m1_fault_input, slit_fault_input, m2_fault_input, m3_fault_input, cp_fault_input])

# Add fault states
sxrss_fault_state_default = models.FaultState(device_state=sxrss_default_state,
                                                     fault=sxrss_fault, default=True)
sxrss_fault_state_ss = models.FaultState(device_state=sxrss_state_ss, fault=sxrss_fault)
sxrss_fault_state_harmonic = models.FaultState(device_state=sxrss_state_harmonic, fault=sxrss_fault)
sxrss_fault_state_sase = models.FaultState(device_state=sxrss_state_sase, fault=sxrss_fault)
session.add_all([sxrss_fault_state_default, sxrss_fault_state_ss,
                 sxrss_fault_state_harmonic, sxrss_fault_state_sase])

sxrss_fault_state_default.add_allowed_class(beam_class=class_0, mitigation_device=shutter)
sxrss_fault_state_harmonic.add_allowed_class(beam_class=class_3, mitigation_device=shutter)
sxrss_fault_state_ss.add_allowed_class(beam_class=class_3, mitigation_device=shutter)
sxrss_fault_state_sase.add_allowed_class(beam_class=class_3, mitigation_device=shutter)

session.commit()
