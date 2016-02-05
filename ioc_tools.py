from mps_config import MPSConfig
import models
import json

def generate_json_for_link_node_ioc(link_node_number):
  mps = MPSConfig()
  session = mps.session
  
  crate = session.query(models.Crate).filter(models.Crate.number == link_node_number).one()
  crate_dict = {"name": "LinkNode{number}".format(number=crate.number)}
  apps = []
  for card in crate.cards:
    card_dict = {}
    card_dict["name"] = "{type}".format(type=card.type.name)
    card_dict["ip"] = ip_address_for_card(card)
    card_dict["port"] = 123456
    
    #Now we'll add register addresses for each threshold map.
    analog_devices = session.query(models.AnalogDevice).join(models.AnalogDevice.channel).filter(models.Channel.card_id == card.id).order_by(models.Channel.number).all()
    registers = []
    address = 0x0C000000
    for analog_device in analog_devices:
      register_dict = {}
      nelm = 256
      value_size = 4
      register_dict["name"] = "_".join(analog_device.name.split())
      register_dict["type"] = "Threshold"
      register_dict["nelm"] = nelm
      register_dict["addr"] = hex(address)
      address += nelm*value_size
      registers.append(register_dict)
    card_dict["reg"] = registers
    apps.append(card_dict)
  crate_dict["apps"] = apps
  return json.dumps(crate_dict, sort_keys=True, indent=2, separators=(',', ': '))
      
def ip_address_for_card(card):
  return "192.168.{shelf_num}.{slot_num}".format(shelf_num=card.crate.shelf_number, slot_num=card.slot_number)