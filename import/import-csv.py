#!/usr/bin/env python
from mps_config import MPSConfig, models
from sqlalchemy import MetaData

class DatabaseImporter:
  conf = None # MPSConfig
  session = None

  def __init__(self, file_name):
    self.conf = MPSConfig(file_name)
    self.conf.clear_all()
    self.session = self.conf.session
    self.session.autoflush=False

  def __del__(self):
    self.session.commit()
    
  def add_crates(self, file_name):
    f = open(file_name)

    line = f.readline().strip()
    fields=[]
    for field in line.split(','):
      fields.append(str(field).lower())

    while line:
      crate_info={}
      line = f.readline().strip()

      if line:
        field_index = 0
        for property in line.split(','):
          crate_info[fields[field_index]]=property
          field_index = field_index + 1

        crate = models.Crate(number=crate_info['number'],
                             num_slots=crate_info['num_slots'],
                             shelf_number=int(crate_info['shelf_number']),
                             location=crate_info['location'],
                             rack=crate_info['rack'],
                             elevation=crate_info['elevation'],
                             sector=crate_info['sector'])
        self.session.add(crate)
      
    self.session.commit()
    f.close()


  def add_app_types(self, file_name):
    f = open(file_name)

    line = f.readline().strip()
    fields=[]
    for field in line.split(','):
      fields.append(str(field).lower())

    while line:
      app_type_info={}
      line = f.readline().strip()

      if line:
        field_index = 0
        for property in line.split(','):
          app_type_info[fields[field_index]]=property
          field_index = field_index + 1

        app_type = models.ApplicationType(number=app_type_info['number'],
                                          name=app_type_info['name'],
                                          digital_channel_count=app_type_info['digital_channel_count'],
                                          digital_channel_size=app_type_info['digital_channel_size'],
                                          digital_out_channel_count=app_type_info['digital_out_channel_count'],
                                          digital_out_channel_size=app_type_info['digital_out_channel_size'],
                                          analog_channel_count=app_type_info['analog_channel_count'],
                                          analog_channel_size=app_type_info['analog_channel_size'])
        self.session.add(app_type)
      
    self.session.commit()
    f.close()

  def add_cards(self, file_name):
    f = open(file_name)

    line = f.readline().strip()
    fields=[]
    for field in line.split(','):
      fields.append(str(field).lower())

    while line:
      app_card_info={}
      line = f.readline().strip()

      if line:
        field_index = 0
        for property in line.split(','):
          app_card_info[fields[field_index]]=property
          field_index = field_index + 1

        app_card_type = self.session.query(models.ApplicationType).\
            filter(models.ApplicationType.number==app_card_info['type_number']).one()

        try:
          app_crate = self.session.query(models.Crate).\
              filter(models.Crate.number==app_card_info['crate_number']).one()
        except:
          print('ERROR: Cannot find crate with number {0}, exiting...'.format(app_card_info['crate_number']))

        app_card = models.ApplicationCard(name=app_card_info['name'],
                                          number=int(app_card_info['number']),
                                          area=app_card_info['area'],
                                          location=app_card_info['location'],
                                          type=app_card_type,
                                          slot_number=int(app_card_info['slot']),
                                          amc=int(app_card_info['amc']),
                                          global_id=int(app_card_info['global_id']),
                                          description="EIC Digital Input/Output")

        app_crate.cards.append(app_card)
        self.session.add(app_card)

    self.session.commit()
    f.close()

  def add_device_types(self, file_name):
    f = open(file_name)

    line = f.readline().strip()
    fields=[]
    for field in line.split(','):
      fields.append(str(field).lower())

    while line:
      device_type_info={}
      line = f.readline().strip()

      if line:
        field_index = 0
        for property in line.split(','):
          device_type_info[fields[field_index]]=property
          field_index = field_index + 1

        device_type = models.DeviceType(name=device_type_info['name'],
                                        description=device_type_info['description'],
                                        num_integrators=int(device_type_info['num_integrators']))

        self.session.add(device_type)

    self.session.commit()
    f.close()

# linac = models.BeamDestination(name="LINAC", description="Linac destination", destination_mask=0x01)
  def add_beam_destinations(self, file_name):
    f = open(file_name)

    line = f.readline().strip()
    fields=[]
    for field in line.split(','):
      fields.append(str(field).lower())

    while line:
      destination_info={}
      line = f.readline().strip()

      if line:
        field_index = 0
        for property in line.split(','):
          destination_info[fields[field_index]]=property
          field_index = field_index + 1

        beam_destination = models.BeamDestination(name=destination_info['name'],
                                                  description=destination_info['description'],
                                                  destination_mask=int(destination_info['destination_mask']))

        self.session.add(beam_destination)

    self.session.commit()
    f.close()

#class_0 = models.BeamClass(number=0,name="Power Class 0",description="No Beam",
#                              integration_window=10, total_charge=100000, min_period=1)
  def add_beam_classes(self, file_name):
    f = open(file_name)

    line = f.readline().strip()
    fields=[]
    for field in line.split(','):
      fields.append(str(field).lower())

    while line:
      class_info={}
      line = f.readline().strip()

      if line:
        field_index = 0
        for property in line.split(','):
          class_info[fields[field_index]]=property
          field_index = field_index + 1

        beam_class = models.BeamClass(number=class_info['number'],
                                      name=class_info['name'],
                                      description=class_info['description'],
                                      integration_window=int(class_info['integration_window']),
                                      total_charge=int(class_info['total_charge']),
                                      min_period=int(class_info['min_period']))

        self.session.add(beam_class)

    self.session.commit()
    f.close()


importer = DatabaseImporter("mps_config_imported.db")

importer.add_crates('import/Crates.csv')
importer.add_app_types('import/AppTypes.csv')
importer.add_cards('import/AppCards.csv')
importer.add_device_types('import/DeviceTypes.csv')
importer.add_beam_destinations('import/BeamDestinations.csv')
importer.add_beam_classes('import/BeamClasses.csv')

#link_node_card = models.ApplicationCard(name="EIC Digital Card", number=100, area="GUNB",
#                                        location="MP10", type=eic_digital_app, slot_number=2, amc=2, #amc=2 -> RTM
#                                        global_id=2, description="EIC Digital Input/Output")
