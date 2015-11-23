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

#Make a link node.
node = models.LinkNode(number=1)
session.add(node)

#Install a card in the link node.
digital_io_type = models.LinkNodeCardType(name="Digital I/O", channel_count=32)
session.add(digital_io_type)

card = models.LinkNodeCard(number=1)
card.link_node = node
card.type = digital_io_type
session.add(card)

#Define some channels for the card.
chans = []
for i in [0,1,2,3]:
  chan = models.LinkNodeChannel(number=i)
  chan.card = card
  chans.append(chan)
  session.add(chan)
  
#Add a device - an OTR screen.
otr_screen = models.Device(name="OTR")
session.add(otr_screen)

#Give the device some inputs.  It has in and out limit switches.
#Connect these limit switches to channels 0 and 1 of our link node card.
otr_out_lim_sw = models.DeviceInput()
otr_out_lim_sw.channel = chans[0]
otr_out_lim_sw.bit_position = 0
otr_out_lim_sw.device = otr_screen
session.add(otr_out_lim_sw)
otr_in_lim_sw = models.DeviceInput()
otr_in_lim_sw.channel = chans[1]
otr_in_lim_sw.bit_position = 1
otr_in_lim_sw.device = otr_screen
session.add(otr_in_lim_sw)

#Define some states for the device.
otr_screen_out = models.DeviceState(name="Out")
otr_screen_out.device = otr_screen
otr_screen_out.value = 1
session.add(otr_screen_out)
otr_screen_in = models.DeviceState(name="In")
otr_screen_in.device = otr_screen
otr_screen_in.value = 2
session.add(otr_screen_in)
otr_screen_moving = models.DeviceState(name="Moving")
otr_screen_moving.device = otr_screen
otr_screen_moving.value = 0
session.add(otr_screen_moving)
otr_screen_broken = models.DeviceState(name="Broken")
otr_screen_broken.device = otr_screen
otr_screen_broken.value = 3
session.add(otr_screen_broken)

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
otr_fault_out = models.FaultState(name="Out")
otr_fault_out.fault = otr_fault
otr_fault_out.value = 1
session.add(otr_fault_out)
otr_fault_in = models.FaultState(name="In")
otr_fault_in.fault = otr_fault
otr_fault_in.value = 2
session.add(otr_fault_in)
otr_fault_moving = models.FaultState(name="Moving")
otr_fault_moving.fault = otr_fault
otr_fault_moving.value = 0
session.add(otr_fault_moving)
otr_fault_broken = models.FaultState(name="Broken")
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
attenuator = models.Device(name="Attenuator")
session.add(attenuator)

#Give the attenuator some inputs
attenuator_out_lim_sw = models.DeviceInput()
attenuator_out_lim_sw.channel = chans[2]
attenuator_out_lim_sw.bit_position = 0
attenuator_out_lim_sw.device = attenuator
session.add(attenuator_out_lim_sw)
attenuator_in_lim_sw = models.DeviceInput()
attenuator_in_lim_sw.channel = chans[3]
attenuator_in_lim_sw.bit_position = 1
attenuator_in_lim_sw.device = attenuator
session.add(attenuator_in_lim_sw)

#Give the attenuator some states
attenuator_out = models.DeviceState(name="Out")
attenuator_out.device = attenuator
attenuator_out.value = 1
session.add(attenuator_out)
attenuator_in = models.DeviceState(name="In")
attenuator_in.device = attenuator
attenuator_in.value = 2
session.add(attenuator_in)
attenuator_moving = models.DeviceState(name="Moving")
attenuator_moving.device = attenuator
attenuator_moving.value = 0
session.add(attenuator_moving)
attenuator_broken = models.DeviceState(name="Broken")
attenuator_broken.device = attenuator
attenuator_broken.value = 3
session.add(attenuator_broken)

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
both_out = models.FaultState(name="Both out")
both_out.fault = otr_atten_fault
both_out.value = 5
session.add(both_out)
both_in = models.FaultState(name="Both in")
both_in.fault = otr_atten_fault
both_in.value = 10
session.add(both_in)
no_atten = models.FaultState(name="OTR in without attenuation")
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

#Save this stuff
session.commit()
