from mps_config import MPSConfig, models
from sqlalchemy import MetaData
#The MPSConfig object points to our database file.
conf = MPSConfig()

#Clear everything out of the database.
conf.clear_all()

#session is a connection to that database.
session = conf.session

#Make a crate.
crate = models.Crate(number=1, shelf_number=1, num_slots=6)
session.add(crate)

#Save this stuff
session.commit()
