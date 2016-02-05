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

#Define a digital I/O card type.
digital_io_type = models.ApplicationCardType(name="Digital I/O", number=0, channel_count=32, channel_size=1)
session.add(digital_io_type)

#Install a digital I/O card in the crate.
card = models.ApplicationCard(number=1)
card.type = digital_io_type
card.slot_number = 1
crate.cards.append(card)
session.add(card)

#Define some channels for the card.
chans = []
for i in range(0,4):
  chan = models.Channel(number=i)
  chan.card = card
  chans.append(chan)
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
session.add(otr_screen)

#Give the device some inputs.  It has in and out limit switches.
#Connect these limit switches to channels 0 and 1 of our link node card.
otr_out_lim_sw = models.DeviceInput()
otr_out_lim_sw.channel = chans[0]
otr_out_lim_sw.bit_position = 0
otr_out_lim_sw.digital_device = otr_screen
session.add(otr_out_lim_sw)
otr_in_lim_sw = models.DeviceInput()
otr_in_lim_sw.channel = chans[1]
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
session.add(attenuator)

#Give the attenuator some inputs
attenuator_out_lim_sw = models.DeviceInput()
attenuator_out_lim_sw.channel = chans[2]
attenuator_out_lim_sw.bit_position = 0
attenuator_out_lim_sw.digital_device = attenuator
session.add(attenuator_out_lim_sw)
attenuator_in_lim_sw = models.DeviceInput()
attenuator_in_lim_sw.channel = chans[3]
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

#Define a PIC card type.
pic_card_type = models.ApplicationCardType(name="PIC", number=1, channel_count=3, channel_size=8)
session.add(pic_card_type)

#Install a PIC card in the crate.
pic_card = models.ApplicationCard(number=2)
pic_card.type = pic_card_type
pic_card.slot_number = 2
crate.cards.append(pic_card)
session.add(pic_card)

#This card has three channels.
pic_chan_0 = models.Channel(number=0)
pic_chan_0.card = pic_card
session.add(pic_chan_0)

pic_chan_1 = models.Channel(number=1)
pic_chan_1.card = pic_card
session.add(pic_chan_1)

pic_chan_2 = models.Channel(number=2)
pic_chan_2.card = pic_card
session.add(pic_chan_2)

#Define a PIC analog device type
pic_device_type = models.AnalogDeviceType(name="PIC")
session.add(pic_device_type)
#All analog device types need a threshold map.
pic_threshold_map = models.ThresholdValueMap(description="Map for generic PICs.")

for i in range(0,5):
  threshold = models.ThresholdValue(threshold=i, value=0.3*i)
  pic_threshold_map.values.append(threshold)
session.add(pic_threshold_map)

pic_device_type.threshold_value_map = pic_threshold_map

#Make a new PIC, hook it up to the card.
pic = models.AnalogDevice(name="PIC 01 Single Shot")
pic.analog_device_type = pic_device_type
pic.channel = pic_chan_0

#Make a new PIC, hook it up to the card.
pic = models.AnalogDevice(name="PIC 01 Slow Integration")
pic.analog_device_type = pic_device_type
pic.channel = pic_chan_2

#Make a new PIC, hook it up to the card.
pic = models.AnalogDevice(name="PIC 01 Fast Integration")
pic.analog_device_type = pic_device_type
pic.channel = pic_chan_1

#Add a fault for the PIC.
pic_fault = models.ThresholdFault(name="PIC 01 Fault")
pic_fault.analog_device = pic

for i in range(0,5):
  state = models.ThresholdFaultState(threshold=i)
  pic_fault.threshold_fault_states.append(state)
  allowed_classes_in_hxr = [class_1, class_2, class_3]
  if i == 2:
    allowed_classes_in_hxr = [class_1, class_2]
  if i == 3:
    allowed_classes_in_hxr = [class_1]
  if i == 4:
    allowed_classes_in_hxr = []
  state.add_allowed_classes(beam_classes=[class_1, class_2, class_3], mitigation_device=gun)
  state.add_allowed_classes(beam_classes=allowed_classes_in_hxr, mitigation_device=hard_kicker)
  state.add_allowed_classes(beam_classes=[class_1, class_2, class_3], mitigation_device=soft_kicker)

#Save this stuff
session.commit()
