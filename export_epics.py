from mps_config import MPSConfig, models
from sqlalchemy import func
import sys
import argparse

#
# Sample Digital Channel record:
#
# record(bi, "CentralNode:DIGIN0") {
#     field(DESC, "Test input")
#     field(DTYP, "asynInt32")
#     field(SCAN, "1 second")
#     field(ZNAM, "OK")
#     field(ONAM, "FAULTED")
#     field(INP, "@asyn(CENTRAL_NODE 0 3)DIGITAL_CHANNEL")
#}

def printRecord(file, recType, recName, fields):
  file.write("record({0}, \"{1}\") {{\n".format(recType, recName))
  for name, value in fields:
    file.write("  field({0}, \"{1}\")\n".format(name, value))
  file.write("}\n\n")

def exportDigitalChannels(file, digitalChannels):
  for digitalChannel in digitalChannels:
    fields=[]
    fields.append(('DESC', 'Crate[{0}], Card[{1}], Channel[{2}]'.
                   format(digitalChannel.card.crate.number,
                          digitalChannel.card.number,
                          digitalChannel.number)))
    fields.append(('DTYP', 'asynInt32'))
    fields.append(('SCAN', '1 second'))
    fields.append(('ZNAM', 'OK'))
    fields.append(('ONAM', 'FAULTED'))
    fields.append(('INP', '@asyn(CENTRAL_NODE {0} 0)DIGITAL_CHANNEL'.format(digitalChannel.id)))
    printRecord(file, 'bi', '$(BASE):{0}'.format(digitalChannel.name), fields)
  file.close()

parser = argparse.ArgumentParser(description='Export EPICS template database')
parser.add_argument('database', metavar='db', type=file, nargs=1, help='database file name (e.g. mps_gun.db)')
parser.add_argument('--digital-channels', metavar='file', type=argparse.FileType('w'), nargs='?', help='epics template file name for digital channels (e.g. digital_channels.template)')

args = parser.parse_args()

mps = MPSConfig(args.database[0].name)
session = mps.session

if (args.digital_channels):
  exportDigitalChannels(args.digital_channels, session.query(models.DigitalChannel).all())

session.close()

