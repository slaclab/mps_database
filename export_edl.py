from Cheetah.Template import Template

from mps_config import MPSConfig, models
from sqlalchemy import func
import sys
import argparse

def generateDeviceInputsEDL(edlFile, templateFile, deviceInputs):
  data=templateFile.read()

  crates=[]
  cards=[]
  channels=[]
  byps=[]
  bypv=[]
  names=[]
  pvs=[]
  latched=[]
  unlatch=[]

  for deviceInput in deviceInputs:
    crates.append(deviceInput.channel.card.crate.number)
    cards.append(deviceInput.channel.card.number)
    channels.append(deviceInput.channel.number)
    byps.append('MPS:DIGITAL:{0}_BYPS'.format(deviceInput.channel.name))
    bypv.append('MPS:DIGITAL:{0}_BYPV'.format(deviceInput.channel.name))
    names.append(deviceInput.channel.name)
    pvs.append('MPS:DIGITAL:{0}'.format(deviceInput.channel.name))
    latched.append('MPS:DIGITAL:{0}_LATCHED'.format(deviceInput.channel.name))
    unlatch.append('MPS:DIGITAL:{0}_UNLATCH'.format(deviceInput.channel.name))
    
  nameSpace={'DEVICE_INPUTS': str(len(deviceInputs)),
             'DI_CRATE': crates,
             'DI_CARD': cards,
             'DI_CHANNEL': channels,
             'DI_BYPS': byps,
             'DI_BYPV': bypv,
             'DI_NAME': names,
             'DI_PV': pvs,
             'DI_PV_LATCHED': latched,
             'DI_PV_UNLATCH': unlatch,
             }

  t = Template(data, searchList=[nameSpace])
  edlFile.write("%s" % t)
  templateFile.close()
  edlFile.close()

#=== MAIN ==================================================================================

parser = argparse.ArgumentParser(description='Export EPICS template database')
parser.add_argument('database', metavar='db', type=file, nargs=1, 
                    help='database file name (e.g. mps_gun.db)')
parser.add_argument('--device-inputs-edl', metavar='file', type=argparse.FileType('w'), nargs='?',
                    help='epics template file name for digital channels (e.g. device_inputs.edl)')
parser.add_argument('--device-inputs-template', metavar='file', type=argparse.FileType('r'), nargs='?',
                    help='Cheetah template file name for digital channels (e.g. device_inputs.tmpl)')

args = parser.parse_args()

mps = MPSConfig(args.database[0].name)
session = mps.session

if (args.device_inputs_edl and args.device_inputs_template):
  generateDeviceInputsEDL(args.device_inputs_edl, args.device_inputs_template,
                          session.query(models.DeviceInput).all())

session.close()

