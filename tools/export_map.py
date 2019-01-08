#!/usr/bin/env python
#
# This script generates maps of link node inputs (using dot). 
# Usage:
#
# 1) Generate single file with all link nodes and inputs (link_nodes.pdf)
#   export_map.py <database.db> --full
#
# 2) Generate file for one link node (<link_node>.pdf)
#   export_map.py <database.db> --ln <link_node>
#
# 3) Generate one file per link node (takes a while)
#   export_map.py <database.db>
#

from mps_config import MPSConfig, models
from mps_names import MpsName
from sqlalchemy import func
import sys
import argparse
import time 
import os

colors=['blue','orange','green','brown','red','magenta','pink']

def printDevices(session, file, d, node, ln_color, mpsName):
  if (d.card_id != None):
    card = session.query(models.ApplicationCard).filter(models.ApplicationCard.id==d.card_id).one()
    crate = session.query(models.Crate).filter(models.Crate.id==card.crate_id).one()
    color = ln_color[crate.link_node.id]
    card_type = session.query(models.ApplicationType).\
        filter(models.ApplicationType.id==card.type_id).one()
    virtual=False
    if (card.amc==3):
      virtual=True
    
    slot_info = 'Slot {0}'.format(card.slot_number)
    pvs = ''
    if d.discriminator=='analog_device':
      device_type='A'
      ch = session.query(models.AnalogChannel).filter(models.AnalogChannel.id==d.channel_id).one()
      pvs = '{0} (ch {1})'.format(mpsName.getAnalogDeviceName(d), ch.number)
    elif d.discriminator=='mitigation_device':
      device_type='M'
      pvs = ''
    else:
      if virtual:
        device_type='D (PV)'
        slot_info = slot_info + " (virtual)"
        pvs = '?'
      else:
        device_type='D'
        if (len(d.inputs) > 0):
          ch = session.query(models.DigitalChannel).filter(models.DigitalChannel.id==d.inputs[0].channel_id).one()
          pvs = '{0} (ch {1})'.format(mpsName.getDeviceInputName(d.inputs[0]), ch.number)
        if (len(d.inputs) > 1):
          for i in d.inputs[1:]:
            ch = session.query(models.DigitalChannel).filter(models.DigitalChannel.id==i.channel_id).one()
            pvs = '{0}\\n{1} (ch {2})'.format(pvs, mpsName.getDeviceInputName(i), ch.number)
      
    if (node == crate.link_node.get_name() or node == 'All'):
      file.write('"{0}" [shape=box, color={1}, label="{2} [{4}]\\n{5}\\n{3} ft"]\n'.\
                   format(d.name, color, d.name, d.z_location, device_type, pvs))
        
def fix(str):
  return str.replace('-','_').replace('/','_').replace('[','_').replace(']','_')

def export(session, file, node):
  file.write("digraph {\n")
  file.write('  label="Map of inputs to Link Node {0}"'.format(node))
  file.write("  node [fontname=\"sansserif\", fontsize=12]\n")

  # write link nodes
  link_nodes = session.query(models.LinkNode).order_by(models.LinkNode.id.asc()).all()
  ln={}
  ln_color={}
  ci = 0
  for l in link_nodes:
    ln[l.id]=l
    ln_color[l.id]=colors[ci]
    ci = (ci + 1) % len(colors)
    if (node == l.get_name()):
      ln_info='{0}\\n{1}\\n'.format(l.get_name(), l.crate.get_name())
      
      for c in l.crate.cards:
        card_type = session.query(models.ApplicationType).\
            filter(models.ApplicationType.id==c.type_id).one()
        ln_info = '{0}\\n{1} (slot {2})'.format(ln_info, card_type.name, c.slot_number)

      file.write('  "{0}" [shape=box3d, color={1}, label="{2}"]\n'.\
                   format(l.get_name(), ln_color[l.id], ln_info))

  # write link node cards
  cards = session.query(models.ApplicationCard).order_by(models.ApplicationCard.crate_id.asc()).all()
  for card in cards:
    crate = session.query(models.Crate).filter(models.Crate.id==card.crate_id).one()
    card_type = session.query(models.ApplicationType).\
        filter(models.ApplicationType.id==card.type_id).one()
        
    if (node == crate.link_node.get_name() or node == 'All'):
      channels = ''
      if (len(card.analog_channels) > 0):
        for ac in card.analog_channels:
          channels = channels + "{0} (ch {1})\\n".format(ac.analog_device.name, ac.number)
      elif (len(card.digital_channels) > 0):
        for dc in card.digital_channels:
          device = session.query(models.DigitalDevice).\
              filter(models.DigitalDevice.id==dc.device_input.digital_device_id).one()
          channels = channels + "{0} (ch {1})\\n".format(device.name, dc.number)

      file.write('  "{0}" [shape=box3d, color={1}, label="{2}"]\n'.\
                   format('c{0}'.format(card.id), ln_color[crate.link_node.id],
                          '{0} (slot {1})\\n\\n{2}'.format(card_type.name, card.slot_number,channels)))

  devices = session.query(models.Device).order_by(models.Device.z_location.asc()).all()

  # write linked list of devices (based on z-location)
  file.write('  {rank=same;')
  for d in devices:
    if (d.card_id != None):
      try:
        card = session.query(models.ApplicationCard).filter(models.ApplicationCard.id==d.card_id).one()
        crate = session.query(models.Crate).filter(models.Crate.id==card.crate_id).one()
        if (node == crate.link_node.get_name() or node == 'All'):
          file.write('"{0}"->'.format(d.name))
      except:
        print 'ERROR: Failed to find card for device {0} {1}'.format(d.name,d.card_id)
  file.write('END}\n')

  # write device information
  mpsName = MpsName(session)
  for d in devices:
    printDevices(session, file, d, node, ln_color, mpsName)

  # device->card edges
  for d in devices:
    if (d.card_id != None):
      card = session.query(models.ApplicationCard).filter(models.ApplicationCard.id==d.card_id).one()
      crate = session.query(models.Crate).filter(models.Crate.id==card.crate_id).one()
      color = ln_color[crate.link_node.id]
      label = d.name

      if (node == crate.link_node.get_name() or node == 'All'):
        if d.discriminator == 'digital_device':
          channel = ''
          for di in d.inputs:
            try:
              ch = session.query(models.DigitalChannel).\
                  filter(models.DigitalChannel.id==di.channel_id).one()
              channel = channel + str(ch.number)
              if len(d.inputs) > 1:
                channel = channel + ","
            except:
              print 'ERROR: Failed to find analog channel for device (name={0}, channel_id={1}'.\
                  format(d.name, d.channel_id)
          if len(d.inputs) > 1:
            channel = channel[:-1]

        else:
          try:
            ch = session.query(models.AnalogChannel).filter(models.AnalogChannel.id==d.channel_id).one()
          except:
            print 'ERROR: Failed to find analog channel for device (name={0}, channel_id={1}'.\
                format(d.name, d.channel_id)
          else:
            channel = ch.number

        file.write('edge [dir=none, color={0}]\n'.format(color))
        file.write('"{0}"->"c{1}" [label="ch {2}"]\n'.format(d.name, card.id, channel))
#        file.write('"c{0}"->"{1}"\n'.format(card.id, ln[crate.link_node.id].get_name()))

  # card->sioc edges
  for c in cards:
      crate = session.query(models.Crate).filter(models.Crate.id==c.crate_id).one()
      color = ln_color[crate.link_node.id]
      label = d.name
      if (node == crate.link_node.get_name() or node == 'All'):
        file.write('edge [dir=none, color={0}]\n'.format(color))
        file.write('"c{0}"->"{1}" [label="s {2}"]\n'.\
                     format(c.id, ln[crate.link_node.id].get_name(), c.slot_number))


  file.write("}\n")
  file.close()

#  for ln in link_nodes:
#    print ln.get_name()

def exportPDF(ln):
  cmd = 'dot -o {0}.pdf -Tpdf {0}.dot'.format(ln)
  os.system(cmd)

#=== MAIN ==================================================================================

parser = argparse.ArgumentParser(description='Export EPICS template database')

parser.add_argument('database', metavar='db', type=file, nargs=1, 
                    help='database file name (e.g. mps_gun.db)')

parser.add_argument('--ln', metavar='link_node_name', type=str, nargs='?',
                    help='generate graph for the specified link node (sioc name)')
parser.add_argument('--full', action='store_true')
parser.add_argument('--output', metavar='output', type=str, nargs='?', 
                    help='directory where the maps are generated')

args = parser.parse_args()

mps = MPSConfig(args.database[0].name)
session = mps.session

output_dir = './'
if (args.output):
  output_dir = args.output
  if (not os.path.isdir(output_dir)):
    print 'ERROR: Invalid output directory {0}'.format(output_dir)
    exit(-1)

if (args.full):
  print 'INFO: Generation single map with all link node inputs'
  name = 'link_nodes'
  dot_file = open('{0}/{1}.dot'.format(output_dir, name), "w")
  export(session, dot_file, 'All')
  exportPDF('{0}/{1}'.format(output_dir,name))
  dot_file.close()
  session.close()
  exit(0)

link_nodes = session.query(models.LinkNode).order_by(models.LinkNode.id.asc()).all()
if (args.ln):
  found = False
  for l in link_nodes:
    if (l.get_name() == args.ln):
      found = True

  if (not found):
    print 'ERROR: Failed to find link node named \"{0}\"'.format(args.ln)
    exit(-1)

  dot_file = open('{0}/{1}.dot'.format(output_dir, args.ln), "w")
  export(session, dot_file, args.ln)
  exportPDF('{0}/{1}'.format(output_dir, args.ln))
  dot_file.close()
else:
  print 'INFO: Generating maps for {0} link nodes'.format(len(link_nodes))
  for ln in link_nodes:
    ln_name = ln.get_name()
    print ' * {0}'.format(ln_name)
    dot_file = open('{0}/{1}.dot'.format(output_dir,ln_name), "w")
    export(session, dot_file, ln_name)
    exportPDF('{0}/{1}'.format(output_dir,ln_name))
    dot_file.close()

session.close()

