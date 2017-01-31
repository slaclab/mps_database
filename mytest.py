from mps_config import MPSConfig, models

#Use the database to make an empty machine state data structure.
#This code is pretty inefficient.
mps = MPSConfig()
session = mps.session

i = 0
for app_card in session.query(models.ApplicationCard).all():
#  print str(i)
#  i = i + 1
  print "crate_id: " + str(app_card.crate_id)
  print "digital_channels: " + str(len(app_card.digital_channels))
  print "analog_channels: " + str(len(app_card.analog_channels))
