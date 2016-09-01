from mps_config import MPSConfig, models
from sqlalchemy import MetaData
#The MPSConfig object points to our database file.
conf = MPSConfig()

#Clear everything out of the database.
conf.clear_all()

#session is a connection to that database.
session = conf.session

#First lets define our mitigation devices.
gun = models.MitigationDevice(name="Gun")
hard_kicker = models.MitigationDevice(name="Hard Kicker")
soft_kicker = models.MitigationDevice(name="Soft Kicker")
session.add_all([gun, hard_kicker, soft_kicker])

#Make some beam classes.
class_1 = models.BeamClass(number=1,name="Class 1")
class_2 = models.BeamClass(number=2,name="Class 2")
class_3 = models.BeamClass(number=3,name="Class 3")
session.add_all([class_1, class_2, class_3])

#Make a crate.
crate = models.Crate(number=1, shelf_number=1, num_slots=6)
session.add(crate)

#Define a mixed-mode link node (One digital AMC, one analog).
mixed_link_node_type = models.ApplicationType(name="Mixed Mode Link Node", number=0, digital_channel_count=4, digital_channel_size=1, analog_channel_count=3, analog_channel_size=8)
#Define a BPM type
bpm_card_type = models.ApplicationType(name="BPM", number=1, digital_channel_count=4, digital_channel_size=1, analog_channel_count=6, analog_channel_size=8)

session.add_all([mixed_link_node_type, bpm_card_type])

#Add one application for everything...
global_app = models.Application(global_id=100,name="MyGlobalApp",description="Generic Application")
session.add(global_app)

#Install a mixed-mode link node card in the crate.
pic_card = models.ApplicationCard(number=1)
pic_card.type = mixed_link_node_type
pic_card.slot_number = 2
crate.cards.append(pic_card)
session.add(pic_card)

#Install a BPM card in the crate.
#bpm_card = models.ApplicationCard(number=2)
#bpm_card.type = bpm_card_type
#bpm_card.slot_number = 3
#crate.cards.append(bpm_card)
#session.add(bpm_card)

#Define some channels for the card.
digital_chans = []
for i in range(0,4):
  chan = models.DigitalChannel(number=i)
  chan.card = pic_card
  digital_chans.append(chan)
  session.add(chan)

#Add a new device type - insertion device
insertion_device_type = models.DeviceType(name="Insertion Device")
session.add(insertion_device_type)
  
#Define some states for the device type.
otr_screen_out = models.DeviceState(name="Out")
otr_screen_out.device_type = insertion_device_type
otr_screen_out.value = 1

otr_screen_in = models.DeviceState(name="In")
otr_screen_in.device_type = insertion_device_type
otr_screen_in.value = 2

otr_screen_moving = models.DeviceState(name="Moving")
otr_screen_moving.device_type = insertion_device_type
otr_screen_moving.value = 0

otr_screen_broken = models.DeviceState(name="Broken")
otr_screen_broken.device_type = insertion_device_type
otr_screen_broken.value = 3

session.add_all([otr_screen_out, otr_screen_in, otr_screen_moving, otr_screen_broken])

#Add a device - an OTR screen.
otr_screen = models.DigitalDevice(name="OTR")
otr_screen.device_type = insertion_device_type
otr_screen.application = global_app
session.add(otr_screen)

#Give the device some inputs.  It has in and out limit switches.
#Connect these limit switches to channels 0 and 1 of our link node card.
otr_out_lim_sw = models.DeviceInput()
otr_out_lim_sw.channel = digital_chans[0]
otr_out_lim_sw.bit_position = 0
otr_out_lim_sw.digital_device = otr_screen
session.add(otr_out_lim_sw)
otr_in_lim_sw = models.DeviceInput()
otr_in_lim_sw.channel = digital_chans[1]
otr_in_lim_sw.bit_position = 1
otr_in_lim_sw.digital_device = otr_screen
session.add(otr_in_lim_sw)

#Configure a fault for the device
otr_fault = models.Fault(name="OTR Fault")
session.add(otr_fault)

#This fault only has one input: the device state.
otr_fault_input = models.FaultInput()
otr_fault_input.bit_position = 0
otr_fault_input.device = otr_screen
otr_fault_input.fault = otr_fault
session.add(otr_fault_input)

#This fault's states match up exactly with the device states.
otr_fault_out = models.DigitalFaultState(name="Out")
otr_fault_out.fault = otr_fault
otr_fault_out.value = 1
session.add(otr_fault_out)
otr_fault_in = models.DigitalFaultState(name="In")
otr_fault_in.fault = otr_fault
otr_fault_in.value = 2
session.add(otr_fault_in)
otr_fault_moving = models.DigitalFaultState(name="Moving")
otr_fault_moving.fault = otr_fault
otr_fault_moving.value = 0
session.add(otr_fault_moving)
otr_fault_broken = models.DigitalFaultState(name="Broken")
otr_fault_broken.fault = otr_fault
otr_fault_broken.value = 3
session.add(otr_fault_broken)

#Give the fault states allowed beam classes.
otr_fault_out.add_allowed_classes(beam_classes=[class_1, class_2, class_3], mitigation_device=gun)
otr_fault_out.add_allowed_classes(beam_classes=[class_1, class_2, class_3], mitigation_device=hard_kicker)
otr_fault_out.add_allowed_classes(beam_classes=[class_1, class_2, class_3], mitigation_device=soft_kicker)

otr_fault_in.add_allowed_class(beam_class=class_1, mitigation_device=gun)
otr_fault_in.add_allowed_classes(beam_classes=[class_1, class_2, class_3], mitigation_device=hard_kicker)
otr_fault_in.add_allowed_classes(beam_classes=[class_1, class_2, class_3], mitigation_device=soft_kicker)

otr_fault_moving.allowed_classes = []
otr_fault_broken.allowed_classes = []

#Add a second device
attenuator = models.DigitalDevice(name="Attenuator")
attenuator.device_type = insertion_device_type
attenuator.application = global_app
session.add(attenuator)

#Give the attenuator some inputs
attenuator_out_lim_sw = models.DeviceInput()
attenuator_out_lim_sw.channel = digital_chans[2]
attenuator_out_lim_sw.bit_position = 0
attenuator_out_lim_sw.digital_device = attenuator
session.add(attenuator_out_lim_sw)
attenuator_in_lim_sw = models.DeviceInput()
attenuator_in_lim_sw.channel = digital_chans[3]
attenuator_in_lim_sw.bit_position = 1
attenuator_in_lim_sw.digital_device = attenuator
session.add(attenuator_in_lim_sw)

#Lets make a fault that uses both devices
otr_atten_fault = models.Fault(name="OTR Attenuation Fault")
session.add(otr_atten_fault)

#This fault looks at both the OTR and the Attenuator
otr_input = models.FaultInput()
otr_input.bit_position = 0
otr_input.device = otr_screen
otr_input.fault = otr_atten_fault
session.add(otr_input)
att_input = models.FaultInput()
att_input.bit_position = 1
att_input.device = attenuator
att_input.fault = otr_atten_fault
session.add(att_input)

#Add some states to this fault.
both_out = models.DigitalFaultState(name="Both out")
both_out.fault = otr_atten_fault
both_out.value = 5
session.add(both_out)
both_in = models.DigitalFaultState(name="Both in")
both_in.fault = otr_atten_fault
both_in.value = 10
session.add(both_in)
no_atten = models.DigitalFaultState(name="OTR in without attenuation")
no_atten.fault = otr_atten_fault
no_atten.value = 6
session.add(no_atten)

#Add some allowed beam classes
both_out.add_allowed_classes(beam_classes=[class_1, class_2, class_3], mitigation_device=gun)
both_out.add_allowed_classes(beam_classes=[class_1, class_2, class_3], mitigation_device=hard_kicker)
both_out.add_allowed_classes(beam_classes=[class_1, class_2, class_3], mitigation_device=soft_kicker)

both_in.add_allowed_class(beam_class=class_1, mitigation_device=gun)
both_in.add_allowed_class(beam_class=class_1, mitigation_device=hard_kicker)
both_in.add_allowed_class(beam_class=class_1, mitigation_device=soft_kicker)

no_atten.allowed_classes = []

#Lets add an analog device, too.

#This PIC has three channels.
pic_chan_0 = models.AnalogChannel(number=0)
pic_chan_0.card = pic_card
session.add(pic_chan_0)

pic_chan_1 = models.AnalogChannel(number=1)
pic_chan_1.card = pic_card
session.add(pic_chan_1)

pic_chan_2 = models.AnalogChannel(number=2, card=pic_card)
#pic_chan_2.card = pic_card
session.add(pic_chan_2)

#Define a PIC analog device type
pic_device_type = models.AnalogDeviceType(name="PIC", units="counts")
session.add(pic_device_type)
#All analog device types need a threshold map.
pic_threshold_map = models.ThresholdValueMap(description="Map for generic PICs.")
for i in range(0,15):
  threshold = models.ThresholdValue(threshold=i, value=0.25*i)
  pic_threshold_map.values.append(threshold)
session.add(pic_threshold_map)

pic_device_type.threshold_value_map = pic_threshold_map

#Make a new PIC, hook it up to the card.  Each PIC integration time is considered a separate device,
# as far as the database is concerned.  In this script, we'll say there are three integration times.
pic_devices = []

pic = models.AnalogDevice(name="PIC 01 Single Shot")
pic.analog_device_type = pic_device_type
pic.channel = pic_chan_0
pic.application = global_app
pic_devices.append(pic)

pic = models.AnalogDevice(name="PIC 01 Fast Integration")
pic.analog_device_type = pic_device_type
pic.channel = pic_chan_1
pic.application = global_app
pic_devices.append(pic)

#Make a new PIC, hook it up to the card.
pic = models.AnalogDevice(name="PIC 01 Slow Integration")
pic.analog_device_type = pic_device_type
pic.channel = pic_chan_2
pic.application = global_app
pic_devices.append(pic)

#attenuator2 = models.DigitalDevice(name="Attenuator2")
#attenuator2.device_type = insertion_device_type
#attenuator2.application = global_app
#session.add(attenuator2)
#session.commit()
session.flush()
session.refresh(pic_device_type)

# Find the thresholds for PIC 1.0 and 2.0 values
tv1 = session.query(models.ThresholdValue).filter(models.ThresholdValue.threshold_value_map_id==pic_device_type.threshold_value_map_id).filter(models.ThresholdValue.value == 1.0).one()
print("Threshold Val: {0} -> {1}; {2}".format(tv1.threshold, tv1.value, tv1.threshold_value_map_id))

tv2 = session.query(models.ThresholdValue).filter(models.ThresholdValue.threshold_value_map_id==pic_device_type.threshold_value_map_id).filter(models.ThresholdValue.value == 2.0).one()
print("Threshold Val: {0} -> {1}; {2}".format(tv2.threshold, tv2.value, tv2.threshold_value_map_id))

#Add some faults for the PIC.  We'll make idential faults for each integration time, but you don't *have* to do that.
for pic in pic_devices:
  pic_fault_1 = models.ThresholdFault(name="PIC Loss > 1.0", greater_than=True, threshold_value=tv1)
  pic_fault_1.analog_device = pic
  threshold_fault_state = models.ThresholdFaultState()
  #This fault will limit the hard line to class 2 or 1, and will not limit any other line.
  threshold_fault_state.add_allowed_classes([class_1, class_2, class_3], mitigation_device=gun)
  threshold_fault_state.add_allowed_classes([class_1, class_2, class_3], mitigation_device=soft_kicker)
  threshold_fault_state.add_allowed_classes([class_1, class_2], mitigation_device=hard_kicker)
  pic_fault_1.threshold_fault_state = threshold_fault_state

  pic_fault_2 = models.ThresholdFault(name="PIC Loss > 2.0", greater_than=True, threshold_value=tv2)
  pic_fault_2.analog_device = pic
  threshold_fault_state = models.ThresholdFaultState()
  #This fault will limit the hard line to class 1 only, and will not limit any other line.
  threshold_fault_state.add_allowed_classes([class_1, class_2, class_3], mitigation_device=gun)
  threshold_fault_state.add_allowed_classes([class_1, class_2, class_3], mitigation_device=soft_kicker)
  threshold_fault_state.add_allowed_class(class_1, mitigation_device=hard_kicker)
  pic_fault_2.threshold_fault_state = threshold_fault_state

#Install a BPM card in the crate.
bpm_card = models.ApplicationCard(number=2)
bpm_card.type = bpm_card_type
bpm_card.slot_number = 3
crate.cards.append(bpm_card)

session.flush()
session.refresh(crate)
print("crate_id: {}".format(crate.id))

session.add(bpm_card)
#session.flush()
#session.commit()

#Define a BPM position analog device type
bpm_position_type = models.AnalogDeviceType(name="BPM Position", units="mm")
session.add(bpm_position_type)
bpm_threshold_map = models.ThresholdValueMap(description="Map for generic BPMs.")
for i in range(0,255): #Map 0-255 to -10mm to +10mm
  threshold = models.ThresholdValue(threshold=i, value=10.0*(i-127.5)/127.5)
  bpm_threshold_map.values.append(threshold)
session.add(bpm_threshold_map)
bpm_position_type.threshold_value_map = bpm_threshold_map

session.flush()
session.refresh(bpm_threshold_map)

#Define a BPM TMIT analog device type
bpm_tmit_type = models.AnalogDeviceType(name="BPM TMIT", units="pC")
session.add(bpm_tmit_type)
bpm_threshold_map = models.ThresholdValueMap(description="Map for generic BPMs.")
for i in range(0,255): #Map 0-255 to 0 pC to 1000 pC
  threshold = models.ThresholdValue(threshold=i, value=1000.0*(i)/255.0)
  bpm_threshold_map.values.append(threshold)
session.add(bpm_threshold_map)
bpm_tmit_type.threshold_value_map = bpm_threshold_map

session.flush()
session.refresh(bpm_threshold_map)

# Find the closest threshold to 1mm
tv_1mm = session.query(models.ThresholdValue).filter(models.ThresholdValue.threshold_value_map_id==bpm_position_type.threshold_value_map_id).filter(models.ThresholdValue.value <= 1.0).order_by(models.ThresholdValue.value.desc()).first()
print("Threshold Val: {0} -> {1}; {2}".format(tv_1mm.threshold, tv_1mm.value, tv_1mm.threshold_value_map_id))

# Find the closest threshold to 150pC
tv_150pC = session.query(models.ThresholdValue).filter(models.ThresholdValue.threshold_value_map_id==bpm_tmit_type.threshold_value_map_id).filter(models.ThresholdValue.value <= 150.0).order_by(models.ThresholdValue.value.desc()).first()
print("Threshold Val: {0} -> {1}; {2}".format(tv_150pC.threshold, tv_150pC.value, tv_150pC.threshold_value_map_id))

#The BPM card has six analog channels: Two BPMs, each with X,Y,and TMIT channels.
bpm_devices = []
channel_number = 0
bpm_channels = ["X", "Y", "TMIT"]
bpm_names = ["BPM 01", "BPM 02"]
for bpm_name in bpm_names:
  for bpm_channel_name in bpm_channels:
    bpm_chan = models.AnalogChannel(number=channel_number) #, card=bpm_card)
    bpm_chan.card = bpm_card
    session.add(bpm_chan)

    bpm_device = models.AnalogDevice(name="{name} {chan}".format(name=bpm_name, chan=bpm_channel_name))
    bpm_device.channel = bpm_chan
    bpm_device.application = global_app
    bpm_devices.append(bpm_device)
    session.add(bpm_device)

    channel_number += 1
    if bpm_channel_name == "TMIT":
      bpm_device.analog_device_type = bpm_tmit_type
      bpm_fault = models.ThresholdFault(name="{name} TMIT < 150 pC".format(name=bpm_name), greater_than=False, threshold_value=tv_150pC)
      bpm_fault.analog_device = bpm_device
      bpm_fault.threshold_fault_state = models.ThresholdFaultState()
      bpm_fault.threshold_fault_state.add_allowed_classes([class_1], mitigation_device=gun)
      bpm_fault.threshold_fault_state.add_allowed_classes([class_1, class_2, class_3], mitigation_device=soft_kicker)
      bpm_fault.threshold_fault_state.add_allowed_classes([class_1, class_2, class_3], mitigation_device=hard_kicker)
    else:
      bpm_device.analog_device_type = bpm_position_type
      bpm_fault = models.ThresholdFault(name="{name} {chan} Position > 1 mm".format(name=bpm_name, chan=bpm_channel_name), greater_than=True, threshold_value=tv_1mm)
      bpm_fault.analog_device = bpm_device
      bpm_fault.threshold_fault_state = models.ThresholdFaultState()
      bpm_fault.threshold_fault_state.add_allowed_classes([class_1], mitigation_device=gun)
      bpm_fault.threshold_fault_state.add_allowed_classes([class_1, class_2, class_3], mitigation_device=soft_kicker)
      bpm_fault.threshold_fault_state.add_allowed_classes([class_1, class_2, class_3], mitigation_device=hard_kicker)
      
#Save this stuff
session.commit()
