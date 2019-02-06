#!/usr/bin/env python

from mps_config import MPSConfig, models
import os
import sys
import argparse
import subprocess
import time
from mps_names import MpsName
from docbook import DocBook

class Exporter:
  databaseFileName=""
  mpsName=0
  session=0
  f=0
  siocPv='SIOC:SYS0:MP01'
  beamDestinationNames=[]
  checkout=True
  cards_only=False
  devices_only=False
  checkout_only=False
  ignore_only=False
  general_only=False
  verbose=False

  def __init__(self, dbFileName, general_only, ignore_only, verbose):
    self.databaseFileName = dbFileName
    mps = MPSConfig(args.database[0].name)
    self.session = mps.session
    self.mpsName = MpsName(self.session)
    self.verbose = verbose
    self.ignore_only = ignore_only
    self.general_only = general_only

    beamDestinations = self.session.query(models.BeamDestination).\
        order_by(models.BeamDestination.destination_mask.asc())
    for d in beamDestinations:
      self.beamDestinationNames.append(d.name.lower())
  
  def __del__(self):
    self.session.close()

  def getAuthor(self):
    proc = subprocess.Popen('whoami', stdout=subprocess.PIPE)
    user = proc.stdout.readline().rstrip()
    email = ""
    name = ""
    first_name = "unknown"
    last_name = "unknown"
    proc = subprocess.Popen(['person', '-tag', '-search', 'email', user], stdout=subprocess.PIPE)
    while True:
      line = proc.stdout.readline()
      if line != '':
        if line.startswith("email") and email == "":
          email = line.split(':')[1].rstrip() + "@slac.stanford.edu"
        elif line.startswith("name") and name == "":
          name = line.split(':')[1].rstrip()
          first_name = name.split(', ')[1]
          last_name = name.split(', ')[0]
      else:
        break

    return [user, email, first_name, last_name]

  def writeDatabaseInfo(self):
    self.docbook.openSection('Database Information')
    info = self.getAuthor()

    cols=[{'name':'c1', 'width':'0.3*'},
          {'name':'c2', 'width':'0.7*'}]

    rows=[]
    rows.append(['Generated on', time.asctime(time.localtime(time.time()))])
    rows.append(['Author', '{0}, {1}'.format(info[3], info[2])])
    rows.append(['E-mail', info[1]])
    rows.append(['Username', info[0]])
    rows.append(['Database source', self.databaseFileName])

    cmd = "md5sum {0}".format(self.databaseFileName)
    process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
    md5sum_output, error = process.communicate()
    md5sum_tokens = md5sum_output.split()
    rows.append(['Database file MD5SUM', md5sum_tokens[0].strip()])
    
    self.docbook.table('Database Information', cols, None, rows, 'database_info_table')
    self.docbook.closeSection()

  def writeDigitalFault(self, fault, device):
    self.docbook.openSection('{0} Faults'.format(device.name))

    channelName = []
    channelBitPos = []
    channelCrateId = []
    channelCrate = []
    channelSlot = []
    channelNumber = []
    channelPv = []
    channelDeviceInput = []

    num_bits = 0

    inp = device.inputs
    ins = sorted(inp, key=lambda i: i.bit_position, reverse=True)
#    print device.name
#    for i in ins:
#      print i.bit_position

    for ddi in ins: #device.inputs:
      channel = self.session.query(models.DigitalChannel).\
          filter(models.DigitalChannel.id==ddi.channel_id).one()
      card = self.session.query(models.ApplicationCard).\
          filter(models.ApplicationCard.id==channel.card_id).one()
      crate = self.session.query(models.Crate).\
          filter(models.Crate.id==card.crate_id).one()
      num_bits = num_bits + 1

      channelName.append(channel.name)
      channelBitPos.append(ddi.bit_position)
      channelCrateId.append(crate.id)
      channelCrate.append(crate.location + '-' + crate.rack + str(crate.elevation))
      channelSlot.append(str(card.slot_number))
      channelNumber.append(str(channel.number))
      channelPv.append(self.mpsName.getDeviceInputName(ddi) + "_MPSC")
      channelDeviceInput.append(ddi)

    numBeamDestinations = self.session.query(models.BeamDestination).count()

    # Fault Table
    cols=[]
    for b in range (0, num_bits):
      cols.append({'name':'b{0}'.format(b), 'width':'0.05*'})
    cols.append({'name':'v1', 'width':'0.05*'})
    cols.append({'name':'f1', 'width':'0.25*'})
    for d in range (0, numBeamDestinations):
      cols.append({'name':'m{0}'.format(d), 'width':'0.10*'})

    header=[]
    var = 'A'
    ivar = num_bits - 1
    for b in range(0, num_bits):
      header.append({'name':'{0}'.format(var), 'namest':None, 'nameend':None})
      var = chr(ord(var) + 1)
      ivar = ivar - 1
    header.append({'name':'Value', 'namest':None, 'nameend':None})
    header.append({'name':'Fault Name', 'namest':None, 'nameend':None})
    beamDestinations = self.session.query(models.BeamDestination).\
        order_by(models.BeamDestination.destination_mask.asc())
    beamDest={}
    for m in beamDestinations:
      beamDest[m.name.lower()] = '-'
      header.append({'name':m.name, 'namest':None, 'nameend':None})

    rows=[]
    for state in fault.states:
      row=[]
      deviceState = self.session.query(models.DeviceState).\
          filter(models.DeviceState.id==state.device_state_id).one()
      bits = []
      maskBits = []
      value = deviceState.value
      mask = deviceState.mask
#      print('{0}; val={1}, mask={2}'.format(deviceState.name, hex(deviceState.value), hex(deviceState.mask)))
      for b in range(0, num_bits):
        bits.append((value & (1 << (num_bits - 1 - b))) >> (num_bits -1 -b))
        maskBits.append((mask & (1 << (num_bits - 1 - b))) >> (num_bits -1 -b))
        if (maskBits[b] == 0):
          input_value = "-"
        else:
          input_value = bits[b]
          if (state.default == True):
            input_value = "default"

          for c in state.allowed_classes:
            beamClass = self.session.query(models.BeamClass).\
                filter(models.BeamClass.id==c.beam_class_id).one()
            beamDestination = self.session.query(models.BeamDestination).\
                filter(models.BeamDestination.id==c.beam_destination_id).one()
#            print device.name + ' - ' + beamDestination.name + ': ' + beamClass.name
            beamDest[beamDestination.name.lower()] = beamClass.name

          # end for
          row.append(input_value)

      row.append(hex(deviceState.value))
      row.append(deviceState.name)
      for key in self.beamDestinationNames:
        row.append(beamDest[key])
      rows.append(row)

      self.tf.write('[FaultState {0} : Fault {1} : DeviceState {2}] Name: {3}; Value: {4}; Mask: {5}; Desc: {6}'.\
                      format(state.id, fault.id, deviceState.id,
                             deviceState.name, hex(deviceState.value),
                             hex(deviceState.mask), deviceState.description))
      for key in beamDest:
        self.tf.write('; {0}: {1}'.format(key, beamDest[key]))
      self.tf.write('\n')

    table_name = '{0} Fault States'.format(device.name)
    table_id = 'fault_state_table.{0}'.format(fault.id)
    self.docbook.table(table_name, cols, header, rows, table_id)

    # Fault Inputs
    table_name = '{0} Fault Inputs'.format(fault.name)
    table_id = 'fault_input_table.{0}.{1}'.format(fault.id, device.id)
    
    cols=[{'name':'c1', 'width':'0.08*'},
          {'name':'b1', 'width':'0.08*'},
          {'name':'c2', 'width':'0.25*'},
          {'name':'c3', 'width':'0.20*'},
          {'name':'c4', 'width':'0.08*'},
          {'name':'c5', 'width':'0.08*'},
          {'name':'c6', 'width':'0.50*'}]

    header=[{'name':'Input', 'namest':None, 'nameend':None},
            {'name':'Bit', 'namest':None, 'nameend':None},
            {'name':'Name', 'namest':None, 'nameend':None},
            {'name':'Crate', 'namest':None, 'nameend':None},
            {'name':'Slot', 'namest':None, 'nameend':None},
            {'name':'Ch #', 'namest':None, 'nameend':None},
            {'name':'PV', 'namest':None, 'nameend':None}]

    rows=[]
    var = 'A'
    for b in range(0, num_bits):
      if (self.devices_only):
        rows.append([var, channelBitPos[b], channelName[b], channelCrate[b],
                     channelSlot[b], channelNumber[b], channelPv[b]])
      else:
        rows.append([var, channelBitPos[b], channelName[b], '<link linkend=\'crate.{0}\'>{1}</link>'.format(channelCrateId[b], channelCrate[b]),
                     channelSlot[b], channelNumber[b], channelPv[b]])
      var = chr(ord(var) + 1)
#      self.tf.write('aoeu[FaultInput {0} : Fault {1}] Name:{2}; Value: {3}; Mask: {4}\n'.\
#                      format(state.id, fault.id, deviceState.name,
#                             hex(deviceState.value), hex(deviceState.mask)))

    self.docbook.table(table_name, cols, header, rows, table_id)
    self.docbook.closeSection()

    # Fault Checkout Table
    if (self.checkout):
      self.docbook.openSection('{0} Checkout'.format(fault.name))

      self.docbook.para('Check all fault input combinations listed in tables "<xref linkend="fault_state_table.{0}"/>" and "<xref linkend="fault_input_table.{0}.{1}"/>". For each fault state verify the inputs and make sure the fault PV is in the faulted state (Fault PV in table "<xref linkend="device_faults_table.{1}"/>"). Write down the power class for each beam destination. The power levels must match the ones listed in the "<xref linkend="fault_state_table.{0}"/>" table.'.format(fault.id, device.id))

      table_name = '{0} Fault Checkout'.format(fault.name)
      table_id = 'fault_checkout_table.{0}.{1}'.format(fault.id, device.id)

      cols=[]
      cols.append({'name':'fault1', 'width':'0.10*'})
      cols.append({'name':'fault2', 'width':'0.50*'})
      for i in range(0, numBeamDestinations):
        cols.append({'name':'m{0}'.format(i), 'width':'0.10*'})

      header=[]
      header.append({'name':'Fault Name', 'namest':'fault1', 'nameend':'fault2'})
      beamDestinations = self.session.query(models.BeamDestination).\
          order_by(models.BeamDestination.destination_mask.asc())
      beamDest={}

      for m in beamDestinations:
        beamDest[m.name.lower()] = '-'
        header.append({'name':m.name, 'namest':None, 'nameend':None})

      rows=[]
      for state in fault.states:
        deviceState = self.session.query(models.DeviceState).\
            filter(models.DeviceState.id==state.device_state_id).one()
        row=[]
        row.append(' ')
  #      row.append('<mediaobject><imageobject condition="print"><imagedata contentwidth="0.5cm" fileref="checkbox.png"/></imageobject><imageobject condition="web"><imagedata fileref="http://www.slac.stanford.edu/~lpiccoli/checkbox.png"/></imageobject></mediaobject>')
        row.append(deviceState.name)
        for key in beamDest:
          row.append(' ')
  #        row.append('<mediaobject><imageobject condition="print"><imagedata contentwidth="0.5cm" fileref="checkbox.png"/></imageobject><imageobject condition="web"><imagedata fileref="http://www.slac.stanford.edu/~lpiccoli/checkbox.png"/></imageobject></mediaobject>')

        rows.append(row)

      self.docbook.table(table_name, cols, header, rows, table_id)
      self.docbook.closeSection()

  def writeAnalogFault(self, fault, device):
    if (self.verbose):
      print 'INFO: Analog fault {} for device {}'.format(fault.name, device.name)

    num_bits = 0

    channelName = []
    channelCrate = []
    channelSlot = []
    channelNumber = []
    channelMask = []
    channelPv = []
    channelId = []
    channelFaultState = []
    channelDeviceState = []

    integratorShift = 0
    if ("X" in fault.name or "I0" in fault.name or "CHARGE" in fault.name or "T0" in fault.name):
      integratorShift = 0
    elif ("Y" in fault.name or "I1" in fault.name or "DIFF" in fault.name):
      integratorShift = 8
    elif ("TMIT" in fault.name or "I2" in fault.name):
      integratorShift = 16
    elif ("I3" in fault.name):
      integratorShift = 24
    else:
      print "ERROR: Can't recognize fault name {0}".format(fault.name)
      exit(-1)

    for state in fault.states:
      deviceState = self.session.query(models.DeviceState).\
          filter(models.DeviceState.id==state.device_state_id).one()
      channel = self.session.query(models.AnalogChannel).\
          filter(models.AnalogChannel.id==device.channel_id).one()
      card = self.session.query(models.ApplicationCard).\
          filter(models.ApplicationCard.id==channel.card_id).one()
      crate = self.session.query(models.Crate).\
          filter(models.Crate.id==card.crate_id).one()

      channelId.append(str(channel.id))
      channelName.append(deviceState.name)
      channelCrate.append(str(crate.crate_id))
      channelSlot.append(str(card.slot_number))
      channelNumber.append(str(channel.number))
      channelMask.append(str(hex((deviceState.mask >> integratorShift) & 0xFF)))
      channelPv.append(self.mpsName.getAnalogDeviceName(device) + ":" + state.device_state.name)
      channelFaultState.append(state)
      channelDeviceState.append(deviceState)

    self.docbook.para('Table "<xref linkend="fault_states.{1}{4}"/>" lists the {0} fault input bits for the {2} device. MPS supports up to eight comparators for {0}, this database version {3}.'.format(fault.name, fault.id, device.name, len(fault.states), device.id))

    # Fault States
    table_name = '{0} Fault States'.format(fault.name)
    table_id = 'fault_states.{0}{1}'.format(fault.id, device.id)

    max_bits = 8 # max number of analog thresholds
    numBeamDestinations = self.session.query(models.BeamDestination).count()

    cols=[]
    for b in range(0, max_bits):
      cols.append({'name':'b{0}'.format(b), 'width':'0.05*'})
    cols.append({'name':'f2', 'width':'0.30*'})
    for m in range(0, numBeamDestinations):
      cols.append({'name':'m{0}'.format(m), 'width':'0.20*'})

    header=[]
    var = '7'
    for b in range(0, max_bits):
      header.append({'name':var, 'namest':None, 'nameend':None})
      var = chr(ord(var) - 1)
    header.append({'name':'Fault Name', 'namest':None, 'nameend':None})
    beamDest={}
    beamDestinations = self.session.query(models.BeamDestination).\
        order_by(models.BeamDestination.destination_mask.asc())
    for m in beamDestinations:
      beamDest[m.name.lower()] = '-'
      header.append({'name':m.name, 'namest':None, 'nameend':None})

    rows=[]
    rowIndex = 0
    for state in fault.states:
      row=[]

      num_bits = num_bits + 1
      deviceState = self.session.query(models.DeviceState).\
          filter(models.DeviceState.id==state.device_state_id).one()
      channel = self.session.query(models.AnalogChannel).\
          filter(models.AnalogChannel.id==device.channel_id).one()
      card = self.session.query(models.ApplicationCard).\
          filter(models.ApplicationCard.id==channel.card_id).one()
      crate = self.session.query(models.Crate).\
          filter(models.Crate.id==card.crate_id).one()

      v = 0x80
      actualValue = (deviceState.value >> integratorShift) & 0xFF
      for b in range(0, max_bits):
        if (v & actualValue > 0):
          row.append('1')
        else:
          row.append('-')
        v = (v >> 1)

        for c in state.allowed_classes:
          beamClass = self.session.query(models.BeamClass).filter(models.BeamClass.id==c.beam_class_id).one()
          beamDestination = self.session.query(models.BeamDestination).filter(models.BeamDestination.id==c.beam_destination_id).one()
          beamDest[beamDestination.name.lower()] = beamClass.name
        # end for c
      # end for b
      row.append(fault.name)
      for m in beamDestinations:
        row.append(beamDest[m.name.lower()])
#      for key in beamDest:
#        row.append('+')
#        row.append(beamDest[key])
#        row.append('<mediaobject><imageobject condition="print"><imagedata contentwidth="0.5cm" fileref="checkbox.png"/></imageobject><imageobject condition="web"><imagedata fileref="http://www.slac.stanford.edu/~lpiccoli/checkbox.png"/></imageobject></mediaobject>')
      rows.append(row)

      self.tf.write('[FaultState {0} : Fault {1} : DeviceState {2}] Name: {3}; Value: {4}; Mask: {5}; Desc: {6}'.\
                      format(state.id, fault.id, deviceState.id,
                             deviceState.name, hex(deviceState.value),
                             hex(deviceState.mask), deviceState.description))
      for key in beamDest:
        self.tf.write('; {0}: {1}'.format(key, beamDest[key]))
      self.tf.write('\n')


    # end for state
    self.docbook.table(table_name, cols, header, rows, table_id)

    # Fault Threshold Input Bits
    table_name = '{0} Fault Inputs (thresholds)'.format(fault.name)
    table_id = 'fault_input_table.{0}.{1}'.format(fault.id, device.id)
    
    cols=[{'name':'c1', 'width':'0.08*'},
          {'name':'c2', 'width':'0.25*'},
          {'name':'c3', 'width':'0.15*'},
          {'name':'c4', 'width':'0.15*'},
          {'name':'c5', 'width':'0.15*'},
          {'name':'c6', 'width':'0.35*'},
          {'name':'c7', 'width':'0.50*'}]

    header=[{'name':'Bit', 'namest':None, 'nameend':None},
            {'name':'Name', 'namest':None, 'nameend':None},
            {'name':'Crate', 'namest':None, 'nameend':None},
            {'name':'Slot', 'namest':None, 'nameend':None},
            {'name':'Ch #', 'namest':None, 'nameend':None},
            {'name':'Mask', 'namest':None, 'nameend':None},
            {'name':'PV', 'namest':None, 'nameend':None}]

    rows=[]
    var = '0'
    for b in range(0, num_bits):
      rows.append([var, channelName[b], channelCrate[b],
                   channelSlot[b], channelNumber[b],
                   channelMask[b], channelPv[b]])
      var = chr(ord(var) + 1)
      self.tf.write('[AnalogChannel {0}] GID: {1}; Ch: {2}; Device: {3}; Desc: {4}; PV: {5}\n'.\
                      format(channelId[b], card.global_id, channelNumber[b], device.name, device.description, channelPv[b]))

    self.docbook.table(table_name, cols, header, rows, table_id)

    self.docbook.para('Check all {0} faults caused by inputs crossing the high and low thresholds for all comparators (there are up to eight comparators for each fault (input bits A through H). Only the fault states listed on "<xref linkend="fault_states.{1}{2}"/>" table are defined in this database.'.format(fault.name, fault.id, device.id))

    if (self.checkout):
      self.docbook.para('Table "<xref linkend="fault_checkout_table.{0}.{1}"/>" lists the PVs that should be changed to test the faults. Set the LOW/HIGH PVs with values that cause MPS mitigation actions and write down the power classes.'.format(fault.id, device.id))

      # Fault Checkout Table
      table_name = '{0} Fault Checkout'.format(fault.name)
      table_id = 'fault_checkout_table.{0}.{1}'.format(fault.id, device.id)

      cols=[]
      cols.append({'name':'fault1', 'width':'0.12*'})
      cols.append({'name':'fault2', 'width':'0.35*'})
      cols.append({'name':'threshold1', 'width':'0.65*'})
      cols.append({'name':'threshold2', 'width':'0.25*'})
      for i in range(0, numBeamDestinations):
        cols.append({'name':'m{0}'.format(i), 'width':'0.15*'})

      header=[]
      header.append({'name':'Fault', 'namest':'fault1', 'nameend':'fault2'})
      header.append({'name':'Threshold [PV, Value]', 'namest':'threshold1', 'nameend':'threshold2'})
      beamDest={}
      beamDestinations = self.session.query(models.BeamDestination).\
          order_by(models.BeamDestination.destination_mask.asc())
      for m in beamDestinations:
        beamDest[m.name.lower()] = '-'
        header.append({'name':m.name, 'namest':None, 'nameend':None})

      rows=[]
      for state in fault.states:
        deviceState = self.session.query(models.DeviceState).\
            filter(models.DeviceState.id==state.device_state_id).one()

        thresholdPv = self.mpsName.getAnalogDeviceName(device) + ":" + deviceState.name

        # Low threshold
        row=[]
        row.append(' ')
  #      row.append('<mediaobject><imageobject condition="print"><imagedata contentwidth="0.5cm" fileref="checkbox.png"/></imageobject><imageobject condition="web"><imagedata fileref="http://www.slac.stanford.edu/~lpiccoli/checkbox.png"/></imageobject></mediaobject>')
        row.append('{0} (Low)'.format(deviceState.name))
        row.append('{0}_L'.format(thresholdPv))
        row.append(' ')
  #      row.append('<mediaobject><imageobject condition="print"><imagedata contentdepth="0.5cm" fileref="checkbox-long.png"/></imageobject><imageobject condition="web"><imagedata fileref="http://www.slac.stanford.edu/~lpiccoli/checkbox-long.png"/></imageobject></mediaobject>')
        for key in beamDest:
          row.append(' ')
  #        row.append('<mediaobject><imageobject condition="print"><imagedata contentwidth="0.5cm" fileref="checkbox.png"/></imageobject><imageobject condition="web"><imagedata fileref="http://www.slac.stanford.edu/~lpiccoli/checkbox.png"/></imageobject></mediaobject>')
        rows.append(row)

        # High threshold
        row=[]
        row.append(' ')
  #      row.append('<mediaobject><imageobject condition="print"><imagedata contentwidth="0.5cm" fileref="checkbox.png"/></imageobject><imageobject condition="web"><imagedata fileref="http://www.slac.stanford.edu/~lpiccoli/checkbox.png"/></imageobject></mediaobject>')
        row.append('{0} (High)'.format(deviceState.name))
        row.append('{0}_H'.format(thresholdPv))
        row.append(' ')
  #      row.append('<mediaobject><imageobject condition="print"><imagedata contentdepth="0.5cm" fileref="checkbox-long.png"/></imageobject><imageobject condition="web"><imagedata fileref="http://www.slac.stanford.edu/~lpiccoli/checkbox-long.png"/></imageobject></mediaobject>')
        for key in beamDest:
          row.append(' ')
  #        row.append('<mediaobject><imageobject condition="print"><imagedata contentwidth="0.5cm" fileref="checkbox.png"/></imageobject><imageobject condition="web"><imagedata fileref="http://www.slac.stanford.edu/~lpiccoli/checkbox.png"/></imageobject></mediaobject>')
        rows.append(row)

      self.docbook.table(table_name, cols, header, rows, table_id)

  def writeFault(self, fault, device):
    self.docbook.openSection('{0} Fault'.format(fault.name), 'fault.{0}.{1}'.format(fault.id, device.id))
    if (self.verbose):
      print 'INFO: {} Fault (id={}, device={}, inputs={})'.\
          format(fault.name, fault.id, device.name, len(fault.inputs))

    for inp in fault.inputs:
      if (inp.device_id == device.id):
        digital = True
        try:
          digitalDevice = self.session.query(models.DigitalDevice).\
              filter(models.DigitalDevice.id==inp.device_id).one()
          self.writeDigitalFault(fault, digitalDevice)
        except:
          digital = False

        if (not digital):
          try:
            analogDevice = self.session.query(models.AnalogDevice).\
                filter(models.AnalogDevice.id==inp.device_id).one()
          except:
            print("ERROR: Can't find device for fault[{0}] (fault id={1}, desc[{2}], device id: {3}, fault_input id: {4}".\
                    format(fault.name, fault.id, fault.description, inp.device_id, inp.id))
            exit(-1)
          self.writeAnalogFault(fault, analogDevice)

    self.docbook.closeSection()

  def writeDeviceFaults(self, device):
    self.docbook.openSection('{0} Faults'.format(device.name))
    if (self.verbose):
      print 'INFO: {} Faults'.format(device.name)

    cols=[{'name':'c1', 'width':'0.25*'},
          {'name':'c2', 'width':'0.45*'},
          {'name':'c3', 'width':'0.75*'}]

    header=[{'name':'Name', 'namest':None, 'nameend':None},
            {'name':'Description', 'namest':None, 'nameend':None},
            {'name':'Fault PV', 'namest':None, 'nameend':None}]

    rows=[]
    for fault_input in device.fault_outputs:
      fault = self.session.query(models.Fault).filter(models.Fault.id==fault_input.fault_id).one()
      rows.append(['<link linkend=\'fault.{0}.{2}\'>{1}</link>'.format(fault.id, fault.name, device.id),
                   fault.description, self.mpsName.getFaultName(fault)])
      self.tf.write('[Fault {0}] Name: {1}; DeviceId: {2}; DeviceName: {3}\n'.
                    format(fault.id, fault.name, device.id, device.name))


    table_name = '{0} Faults'.format(device.name)
    table_id = 'device_faults_table.{0}'.format(device.id)
    self.docbook.table(table_name, cols, header, rows, table_id)

    if (self.verbose):
      print 'INFO: {} device fault outputs found'.format(len(device.fault_outputs))

    for fault_input in device.fault_outputs:
      fault = self.session.query(models.Fault).filter(models.Fault.id==fault_input.fault_id).one()
      self.writeFault(fault, device)

    self.docbook.closeSection()

  def writeDeviceInfo(self, device):
    keys = ['name', 'description', 'area', 'position']

    self.docbook.openSection(device.name, 'device.{0}'.format(device.id))

    if (self.checkout_only):
      cols=[{'name':'c1', 'width':'0.25*'},
            {'name':'c2', 'width':'0.75*'}]

      header=[{'name':'Property', 'namest':None, 'nameend':None},
              {'name':'Value', 'namest':'zero1', 'nameend':'zero2'}]

      self.tf.write('[Device {0}] '.format(device.id))
      rows=[]
      for k in keys:
        if not k.startswith('_'):
          rows.append([k.title(), getattr(device, k)])
          self.tf.write('{0}: {1}; '.format(k.title(), getattr(device, k)))
      self.tf.write('\n')

      dt = self.session.query(models.DeviceType).filter(models.DeviceType.id==device.device_type_id).one()
      rows.append(['type', dt.name])

      cols=[{'name':'c1', 'width':'0.25*'},
            {'name':'c2', 'width':'0.75*'}]

      header=[{'name':'Property', 'namest':None, 'nameend':None},
              {'name':'Value', 'namest':'zero1', 'nameend':'zero2'}]

      table_name = '{0} Properties'.format(device.name)
      table_id = 'device_table.{0}'.format(device.id)
      self.docbook.table(table_name, cols, header, rows, table_id)

      try:
        if (self.session.query(models.DigitalDevice).filter(models.DigitalDevice.id==device.id).one() != 'None'):
          self.writeDeviceStates(device)
      except:
        None

    self.writeDeviceFaults(device)
    
    self.docbook.closeSection()

  # write table with possible states for a digital device
  def writeDeviceStates(self, device):
    self.docbook.openSection('{0} Device States'.format(device.name))
    
    # Device Inputs
    table_name = '{0} Device Inputs'.format(device.name)
    table_id = 'device_input_table.{0}'.format(device.id)

    # Device States
    device_states_table_name = '{0} Device States'.format(device.name)
    device_states_table_id = 'device_states_{0}'.format(device.id)

    self.docbook.para('Table "<link linkend=\'device_input_table.{0}\'>{2}</link>" lists the digital inputs that compose the {1} device. Each input combination defines a state (table "<link linkend=\'{3}\'>{4}</link>"). Some of the states are considered faults and may have mitigation actions.'.format(device.id, device.name, table_name, device_states_table_id, device_states_table_name))

    channelName = []
    channelBitPos = []
    channelCrateId = []
    channelCrate = []
    channelSlot = []
    channelNumber = []
    channelPv = []
    channelDeviceInput = []

    num_bits = 0

#    print '{0} {1}'.format(device.name, device.id)
    inp = device.inputs
    ins = sorted(inp, key=lambda i: i.bit_position, reverse=True)

    for ddi in ins: #device.inputs:
      channel = self.session.query(models.DigitalChannel).\
          filter(models.DigitalChannel.id==ddi.channel_id).one()
      card = self.session.query(models.ApplicationCard).\
          filter(models.ApplicationCard.id==channel.card_id).one()
      crate = self.session.query(models.Crate).\
          filter(models.Crate.id==card.crate_id).one()
      num_bits = num_bits + 1

      channelName.append(channel.name)
      channelBitPos.append(ddi.bit_position)
      channelCrateId.append(crate.id)
      channelCrate.append(crate.location)# + '-' + crate.rack + str(crate.elevation))
      channelSlot.append(str(card.slot_number))
      channelNumber.append(str(channel.number))
      channelPv.append(self.mpsName.getDeviceInputName(ddi) + "_MPSC")
      channelDeviceInput.append(ddi)

    
    cols=[{'name':'c1', 'width':'0.08*'},
          {'name':'b1', 'width':'0.08*'},
          {'name':'c2', 'width':'0.25*'},
          {'name':'c3', 'width':'0.25*'},
          {'name':'c4', 'width':'0.08*'},
          {'name':'c5', 'width':'0.08*'},
          {'name':'c6', 'width':'0.50*'}]

    header=[{'name':'Input', 'namest':None, 'nameend':None},
            {'name':'Bit', 'namest':None, 'nameend':None},
            {'name':'Name', 'namest':None, 'nameend':None},
            {'name':'Crate', 'namest':None, 'nameend':None},
            {'name':'Slot', 'namest':None, 'nameend':None},
            {'name':'Ch #', 'namest':None, 'nameend':None},
            {'name':'PV', 'namest':None, 'nameend':None}]

    rows=[]
    var = 'A'
    for b in range(0, num_bits):
      if (self.devices_only):
        rows.append([var, channelBitPos[b], channelName[b], channelCrate[b],
                     channelSlot[b], channelNumber[b], channelPv[b]])
      else:
        rows.append([var, channelBitPos[b], channelName[b], '<link linkend=\'crate.{0}\'>{1}</link>'.format(channelCrateId[b], channelCrate[b]),
                     channelSlot[b], channelNumber[b], channelPv[b]])
      var = chr(ord(var) + 1)
#      self.tf.write('aoeu[FaultInput {0} : Fault {1}] Name:{2}; Value: {3}; Mask: {4}\n'.\
#                      format(state.id, fault.id, deviceState.name,
#                             hex(deviceState.value), hex(deviceState.mask)))

    self.docbook.table(table_name, cols, header, rows, table_id)

    table_name = '{0} Device States'.format(device.name)
    table_id = 'device_states_{0}'.format(device.id)

    # Device states table
    cols=[]
    for b in range (0, num_bits):
      cols.append({'name':'b{0}'.format(b), 'width':'0.05*'})
    cols.append({'name':'v1', 'width':'0.05*'})
    cols.append({'name':'f1', 'width':'0.25*'})

    header=[]
    var = 'A'
    ivar = num_bits - 1
    for b in range(0, num_bits):
      header.append({'name':'{0}'.format(var), 'namest':None, 'nameend':None})
      var = chr(ord(var) + 1)
      ivar = ivar - 1
    header.append({'name':'Value', 'namest':None, 'nameend':None})
    header.append({'name':'Device State', 'namest':None, 'nameend':None})

    rows=[]
    device_type = self.session.query(models.DeviceType).\
        filter(models.DeviceType.id==device.device_type_id).one()

    for deviceState in device_type.states:
      row=[]
      bits = []
      maskBits = []
      value = deviceState.value
      mask = deviceState.mask
      for b in range(0, num_bits):
        bits.append((value & (1 << (num_bits - 1 - b))) >> (num_bits -1 -b))
        maskBits.append((mask & (1 << (num_bits - 1 - b))) >> (num_bits -1 -b))
        if (maskBits[b] == 0):
          input_value = "-"
        else:
          input_value = bits[b]

          # end for
          row.append(input_value)

      row.append(hex(deviceState.value))
      row.append(deviceState.name)
      rows.append(row)

      self.tf.write('[FaultState {0} : Fault {1} : DeviceState {2}] Name: {3}; Value: {4}; Mask: {5}; Desc: {6}'.\
#                      format(state.id, fault.id, deviceState.id,
                    format('S', 'F', deviceState.id,
                             deviceState.name, hex(deviceState.value),
                             hex(deviceState.mask), deviceState.description))

      self.tf.write('\n')

#    table_name = '{0} Device States'.format(device.name)
#    table_id = 'device_state_table.{0}'.format(device.id)
    self.docbook.table(device_states_table_name, cols, header, rows, device_states_table_id)

    self.docbook.closeSection()

  def writeDigitalCheckoutTable(self, card, channels):
    self.docbook.openSection('{0} Checkout'.format(card.name))

    self.docbook.para('For every signal in the checkout table change it using the respective subsystem (e.g. Profile Monitor for inserting/removing screen) and verify if the input state changes. Check mark the states making sure they reflect the device state.')

    cols=[{'name':'channel', 'width':'0.12*'},
          {'name':'zero1', 'width':'0.1*'},
          {'name':'zero2', 'width':'0.35*'},
          {'name':'one1', 'width':'0.1*'},
          {'name':'one2', 'width':'0.35*'},
          {'name':'pv', 'width':'0.75*'}]

    header=[{'name':'Ch #', 'namest':None, 'nameend':None},
            {'name':'Low State (0V)', 'namest':'zero1', 'nameend':'zero2'},
            {'name':'High State (24V)', 'namest':'one1', 'nameend':'one2'},
            {'name':'PV', 'namest':None, 'nameend':None}]

    rows=[]

    for c in channels:
      ddi = self.session.query(models.DeviceInput).filter(models.DeviceInput.channel_id==c.id).one()
      device = self.session.query(models.Device).filter(models.Device.id==ddi.digital_device.id).one()

#      rows.append([c.number, '<mediaobject><imageobject condition="print"><imagedata contentwidth="0.5cm" fileref="checkbox.png"/></imageobject><imageobject condition="web"><imagedata fileref="http://www.slac.stanford.edu/~lpiccoli/checkbox.png"/></imageobject></mediaobject>', c.z_name, '<mediaobject><imageobject condition="print"><imagedata contentwidth="0.5cm" fileref="checkbox.png"/></imageobject><imageobject condition="web"><imagedata fileref="http://www.slac.stanford.edu/~lpiccoli/checkbox.png"/></imageobject></mediaobject>', c.o_name, '{0}_MPSC'.format(self.mpsName.getDeviceInputName(ddi))])
      rows.append([c.number, ' ', c.z_name, ' ', c.o_name, '{0}_MPSC'.format(self.mpsName.getDeviceInputName(ddi))])
      self.tf.write('[DigitalChannel {0}] GID: {1}; Ch: {2}; Device: {3}; Desc: {4}; BitPos: {5}; PV: {6}; Zero: {7}; One: {8};\n'.\
                      format(c.id, card.global_id, c.number, device.name, 
                             device.description, ddi.bit_position,
                             '{0}_MPSC'.format(self.mpsName.getDeviceInputName(ddi)),
                             c.z_name, c.o_name))


    table_name = 'Checkout table for digital inputs'
    table_id = 'checkout_table.{0}{1}'.format(card.name, card.id)
    self.docbook.table(table_name, cols, header, rows, table_id)

    self.docbook.closeSection()

  def writeAppCard(self, card):
    if (self.general_only):
      self.docbook.openSection(card.crate.location + ' Slot ' + str(card.slot_number) + ' - '+ card.name)
    else:
      self.docbook.openSection(card.crate.location + ' Slot ' + str(card.slot_number) + ' - '+ card.name, 'card.{0}'.format(card.id))

    crate = self.session.query(models.Crate).filter(models.Crate.id==card.crate_id).one()
    crate_name = crate.location# + '-' + crate.rack + str(crate.elevation)

    keys = ['name', 'description', 'area', 'global_id', 'slot_number']


    # Application Cards
    cols=[{'name':'c1', 'width':'0.25*'},
          {'name':'c2', 'width':'0.75*'}]

    header=[{'name':'Property', 'namest':None, 'nameend':None},
            {'name':'Value', 'namest':None, 'nameend':None}]

    rows=[]
    if (self.devices_only):
      rows.append(['Crate', crate_name])
    else:
      rows.append(['Crate', '<link linkend=\'crate.{0}\'>{1}</link>'.format(crate.id, crate_name)])
    for k in keys:
      if not k.startswith('_'):
        rows.append([k, getattr(card, k)])

    table_name = '{0} Properties'.format(card.name)
    table_id = 'card_table.{0}'.format(card.id)
    self.docbook.table(table_name, cols, header, rows, table_id)

    # Application Card Devices
    digital = True
    if (len(card.digital_channels) > 0):
      channels = card.digital_channels
    elif (len(card.analog_channels) > 0):
      channels = card.analog_channels
      digital = False
    else:
      if (False):
        print 'WARN: no digital or analog channels found for card "name={0}", "location={1}", "slot={2}", "amc={3}"'.\
            format(card.name, card.crate.location, card.slot_number, card.amc)
#      print 'ERROR: no digital or analog channels found for card "name={0}", "location={1}", "slot={2}", "amc={3}" can\'t proceed.'.\
#          format(card.name, card.crate.location, card.slot_number, card.amc)
#      card.show()
      self.docbook.closeSection()
      return
#      exit(-1)

    if (not self.cards_only):

      cols=[{'name':'c1', 'width':'0.20*'},
            {'name':'c2', 'width':'0.20*'},
            {'name':'c3', 'width':'0.60*'}]

      header=[{'name':'Name', 'namest':None, 'nameend':None},
              {'name':'Type', 'namest':None, 'nameend':None},
              {'name':'Description', 'namest':None, 'nameend':None}]

      rows=[]
      for d in card.devices:
        if (d.discriminator != 'mitigation_device'):
          if (self.cards_only):
            rows.append([d.name, d.discriminator, d.description])
          else:
            rows.append(['<link linkend=\'device.{0}\'>{1}</link>'.format(d.id, d.name), d.discriminator, d.description])
        else:
          rows.append([d.name, d.discriminator, d.description])

      table_name = '{0} Devices'.format(card.name)
      table_id = 'card_devices_table.{0}'.format(card.id)
      self.docbook.table(table_name, cols, header, rows, table_id)

    # Application Card Channels
    cols=[{'name':'c1', 'width':'0.1*'},
          {'name':'c2', 'width':'0.4*'},
          {'name':'c3', 'width':'0.4*'}]

    header=[{'name':'Ch #', 'namest':None, 'nameend':None},
            {'name':'Input Device', 'namest':None, 'nameend':None},
            {'name':'Signal', 'namest':None, 'nameend':None}]


    rows=[]
    for c in channels:
      if digital:
        ddi = self.session.query(models.DeviceInput).filter(models.DeviceInput.channel_id==c.id).one()
        device = self.session.query(models.Device).filter(models.Device.id==ddi.digital_device.id).one()
        signal_name = c.name
      else:
        device = self.session.query(models.AnalogDevice).filter(models.AnalogDevice.channel_id==c.id).one()
        signal_name = c.name + ' thresholds'

      rows.append([c.number, device.name, signal_name])
#      self.tf.write('Ch: {0}; Device: {1}; Signal: {2}\n'.\
#                      format(c.number, device.name, signal_name))

    table_name = '{0} Input Channels'.format(card.name)
    table_id = 'card_channels_table.{0}'.format(card.id)
    self.docbook.table(table_name, cols, header, rows, table_id)

    if digital:
      if (len(card.digital_out_channels) > 0):

        # Application Card Channels
        cols=[{'name':'c1', 'width':'0.1*'},
              {'name':'c2', 'width':'0.4*'},
              {'name':'c3', 'width':'0.4*'}]

        header=[{'name':'Ch #', 'namest':None, 'nameend':None},
                {'name':'Output Device', 'namest':None, 'nameend':None},
                {'name':'Signal', 'namest':None, 'nameend':None}]

        out_channels = card.digital_out_channels

        rows=[]
        for c in out_channels:
          mitigation_device = c.mitigation_devices[0]
#          ddi = self.session.query(models.DeviceInput).filter(models.DeviceInput.channel_id==c.id).one()
#          device = self.session.query(models.Device).filter(models.Device.id==ddi.digital_device.id).one()
#          signal_name = c.name

          rows.append([c.number, mitigation_device.name, c.name])

        table_name = '{0} Output Channels (Mitigation)'.format(card.name)
        table_id = 'card_output_channels_table.{0}'.format(card.id)
        self.docbook.table(table_name, cols, header, rows, table_id)

      if (self.checkout):
        self.writeDigitalCheckoutTable(card, channels)

    self.docbook.closeSection()

  def writeAppCards(self, link_node):
    self.docbook.openSection('Application Cards')

    cards = self.session.query(models.ApplicationCard).all()

    if (link_node):
      cards = filter (lambda x : x.crate.link_node.id == link_node.id, cards)

    for card in cards:
      self.writeAppCard(card)

    self.docbook.closeSection()
    
  def writeCrate(self, crate):
    name = crate.get_name()

    self.docbook.openSection(name, 'crate.{0}'.format(crate.id))
    self.tf.write('Crate: {0}\n'.format(name))

    # Application Cards
    if (len(crate.cards) > 0):
      cols=[{'name':'c1', 'width':'0.15*'},
            {'name':'c2', 'width':'0.5*'},
            {'name':'c3', 'width':'0.25*'},
            {'name':'c4', 'width':'0.5*'}]

      header=[{'name':'Slot #', 'namest':None, 'nameend':None},
              {'name':'Application Card', 'namest':None, 'nameend':None},
              {'name':'Global Id', 'namest':None, 'nameend':None},
              {'name':'Card Description', 'namest':None, 'nameend':None}]

      rows=[]
      for card in crate.cards:
        slot_info = ''
        if (not self.general_only):
          slot_info = '<link linkend=\'card.{0}\'>{1}</link>'.format(card.id, card.slot_number)
        rows.append([slot_info, card.name, card.global_id, card.description])
        self.tf.write('[Card {0}] Slot: {1}; Name: {2}; GID: {3}; Desc: {4}\n'.\
                        format(card.id, card.slot_number,card.name, card.global_id, card.description))

      table_name = '{0} Cards'.format(name)
      table_id = 'crate_table.{0}'.format(crate.id)
      self.docbook.table(table_name, cols, header, rows, table_id)

    self.docbook.closeSection()

  def writeMitigationDevices(self, destination):
    self.docbook.openSection('{0}: Mitigation Devices'.format(destination.name))

    if len(destination.mitigation_devices) == 0:
      self.docbook.closeSection()
      return 

    cols=[{'name':'c1', 'width':'0.15*'},
          {'name':'c2', 'width':'0.55*'},
          {'name':'c3', 'width':'0.25*'},
          {'name':'c4', 'width':'0.35*'}]

    header=[{'name':'Name', 'namest':None, 'nameend':None},
            {'name':'Description', 'namest':None, 'nameend':None},
            {'name':'Crate', 'namest':None, 'nameend':None},
            {'name':'Card', 'namest':None, 'nameend':None}]

    rows=[]
    for m in destination.mitigation_devices:
      crate = self.session.query(models.Crate).\
          filter(models.Crate.id==m.card.crate_id).one()
      crate_name = crate.location + '-' + crate.rack + str(crate.elevation)
      if (self.devices_only):
        rows.append([m.name, m.description, crate_name,
                     '<link linkend=\'card.{0}\'>{1} (slot {2})</link>\n'.format(m.card.id, m.card.name, m.card.slot_number)])
      else:
        rows.append([m.name, m.description, '<link linkend=\'crate.{0}\'>{1}</link>\n'.format(crate.id, crate_name),
                     '<link linkend=\'card.{0}\'>{1} (slot {2})</link>\n'.format(m.card.id, m.card.name, m.card.slot_number)])

    table_name = 'Mitigation Devices for {0}'.format(destination.name)
    self.docbook.table(table_name, cols, header, rows, 'mitigation_devices.{0}'.format(destination.id))

    self.docbook.closeSection()

  def writeBeamDestinations(self):

    self.docbook.openSection('Beam Destinations')

    cols=[{'name':'c1', 'width':'0.2*'},
          {'name':'c2', 'width':'0.35*'},
          {'name':'c3', 'width':'0.15*'},
          {'name':'c4', 'width':'0.55*'}]

    header=[{'name':'Name', 'namest':None, 'nameend':None},
            {'name':'Description', 'namest':None, 'nameend':None},
            {'name':'Mask', 'namest':None, 'nameend':None},
            {'name':'PV', 'namest':None, 'nameend':None}]

    rows=[]
    for destination in self.session.query(models.BeamDestination).all():
      pvName = self.siocPv + ":" + destination.name + "_PC"
      rows.append([destination.name, destination.description,
                   str(hex(destination.destination_mask)), pvName])

      pvName = self.siocPv + ":" + destination.name + "_FW_PC"
      rows.append(['', '', '', pvName])

      pvName = self.siocPv + ":" + destination.name + "_SW_PC"
      rows.append(['', '', '', pvName])

    table_name = 'Beam Destinations'
    self.docbook.table(table_name, cols, header, rows, "beam_destination_table")

    for destination in self.session.query(models.BeamDestination).all():
      self.writeMitigationDevices(destination)

    self.docbook.closeSection()
    
  def writePowerClasses(self):

    self.docbook.openSection('Beam Power Classes')

    cols=[{'name':'c1', 'width':'0.05*'},
          {'name':'c2', 'width':'0.15*'},
          {'name':'c3', 'width':'0.25*'},
          {'name':'c4', 'width':'0.25*'},
          {'name':'c5', 'width':'0.20*'},
          {'name':'c6', 'width':'0.25*'}]

    header=[{'name':'Id', 'namest':None, 'nameend':None},
            {'name':'Name', 'namest':None, 'nameend':None},
            {'name':'Description', 'namest':None, 'nameend':None},
            {'name':'Int. Window (uS)', 'namest':None, 'nameend':None},
            {'name':'Min. Period (uS)', 'namest':None, 'nameend':None},
            {'name':'Max. Charge (nC)', 'namest':None, 'nameend':None}]

    rows=[]
    for powerClass in self.session.query(models.BeamClass).all():
      rows.append([powerClass.number, powerClass.name,
                   powerClass.description, powerClass.integration_window,
                   powerClass.min_period, powerClass.total_charge])

    # Beam Power Classes Table
    table_name = 'Beam Power Classes'
    self.docbook.table(table_name, cols, header, rows, "power_classes_table")

    self.docbook.closeSection()
 
  def writeDevices(self, link_node):
    if (self.checkout_only):
      self.docbook.openSection('Devices Checkout')
    else:
      self.docbook.openSection('MPS Devices')

    devices = self.session.query(models.Device).all()

    if (link_node):      
      devices = filter (lambda x : x.card.crate.link_node.id == link_node.id, devices)
    
    for device in devices:
      if (device.name != "AOM" and device.name != "MS"):
        self.writeDeviceInfo(device)
    self.docbook.closeSection()

  def writeLogicCondition(self, condition):
    self.docbook.openSection('{0}: {1}'.format(condition.name, condition.description))

    cols=[{'name':'c1', 'width':'0.35*'},
          {'name':'c2', 'width':'0.35*'},
          {'name':'c3', 'width':'0.25*'}]

    header=[{'name':'Fault', 'namest':None, 'nameend':None},
            {'name':'State', 'namest':None, 'nameend':None},
            {'name':'Bit Position', 'namest':None, 'nameend':None}]

    rows=[]
    for input in condition.condition_inputs:
      faultState = self.session.query(models.FaultState).\
          filter(models.FaultState.id==input.fault_state_id).one()
      deviceState = self.session.query(models.DeviceState).filter(models.DeviceState.id==faultState.device_state_id).one()
      fault = self.session.query(models.Fault).filter(models.Fault.id==faultState.fault_id).one()
      rows.append(['<link linkend=\'fault.{0}.{2}\'>{1}</link>\n'.format(fault.id, fault.name, device.id),
                   deviceState.name, input.bit_position])

    table_name = 'Condition Inputs'
    table_id = 'condition.{0}'.format(condition.id)
    self.docbook.table(table_name, cols, header, rows, table_id)

    self.docbook.para('When the condition inputs in the above "<link linkend=\'condition.{0}\'>table</link>" are met, then the faults generated by the following devices are ignored (bypassed):'.format(condition.id))

    table_name = 'Ignored Devices'
    table_id = 'ignored_devices.{0}'.format(condition.id)

    cols=[{'name':'c1', 'width':'0.9*'}]
    header=[{'name':'Device', 'namest':None, 'nameend':None}]

    rows=[]
    for ignoreCondition in condition.ignore_conditions:
      device = self.session.query(models.AnalogDevice).filter(models.AnalogDevice.id==ignoreCondition.analog_device_id).one()
#      rows.append(device.name)
      rows.append(['<link linkend=\'device.{0}\'>{1}</link>'.format(device.id, device.name)])

    self.docbook.table(table_name, cols, header, rows, table_id)

    self.docbook.closeSection()

  def writeIgnoreLogic(self):
    self.docbook.openSection('Ignore Logic')
    conditions = self.session.query(models.Condition).all()
    if (len(conditions) == 0):
      self.docbook.para('There are no ignore logic conditions defined.')
    else:
      for condition in conditions:
        if (len(condition.condition_inputs) > 0 and
            len(condition.ignore_conditions) > 0):
          self.writeLogicCondition(condition)
    self.docbook.closeSection()

  def writeLinkNodes(self, link_node):
    self.docbook.openSection('Link Nodes')
    self.tf.write('# Link Nodes\n')

    cols=[{'name':'c1', 'width':'0.20*'},
          {'name':'c2', 'width':'0.30*'},
          {'name':'c3', 'width':'0.10*'},
          {'name':'c4', 'width':'0.25*'}]

    header=[{'name':'SIOC', 'namest':None, 'nameend':None},
            {'name':'Crate', 'namest':None, 'nameend':None},
            {'name':'Group', 'namest':None, 'nameend':None},
            {'name':'Drawing', 'namest':None, 'nameend':None},]
    
    rows=[]
    linkNodes = self.session.query(models.LinkNode).all()
    if (link_node):
      linkNodes = [ link_node ]

    for ln in linkNodes:
      sioc_info = '{0}'.format(ln.get_name())
      crate_info = '<link linkend=\'crate.{0}\'>{1}</link>'.format(ln.crate.id, ln.crate.get_name())
      rows.append([sioc_info, crate_info, ln.group, ln.group_drawing])
      self.tf.write('[LN {0}] SIOC: {1}; Crate: {2}\n'.\
                      format(ln.id, sioc_info, ln.crate.get_name()))

    table_name = 'Link Nodes'
    table_id = 'link_nodes'
    self.docbook.table(table_name, cols, header, rows, table_id)

    self.docbook.closeSection()

  def writeCrates(self, link_node):
    self.docbook.openSection('ATCA Crates')
    self.tf.write('# Crates\n')
    crates = self.session.query(models.Crate).all()
    if (link_node):
      crates = filter (lambda x : x.link_node.id == link_node.id, crates)

    for crate in crates:
      self.writeCrate(crate)
    self.docbook.closeSection()

  def exportDocBookLinkNodes(self, output_dir, databaseName):
    link_nodes = self.session.query(models.LinkNode).all()
    for ln in link_nodes:
      devices = self.session.query(models.Device).filter(models.Device.card_id == ln.crate.id).all()
      if (len(devices) > 0):
        fileName = '{0}/{1}.xml'.format(output_dir, ln.get_name())
        fileNameTxt = '{0}/{1}.txt'.format(output_dir, ln.get_name())
        self.exportDocBook(fileName, fileNameTxt, databaseName, ln.get_name())

  def exportDocBook(self, fileName, fileNameTxt, databaseName, linkNode):
    info = self.getAuthor()
    self.tf = open(fileNameTxt, 'w')
    self.docbook = DocBook(fileName)
    if (linkNode):
      self.docbook.writeHeader('{1} [{0}]'.format(databaseName, linkNode), '', '')
    elif (self.ignore_only):
      self.docbook.writeHeader('{0} [Ignore Logic]'.format(databaseName), '', '')
      if (self.verbose):
        print 'INFO: Generating document with ignore conditions'
    elif (self.general_only):
      self.docbook.writeHeader('{0} [General Information]'.format(databaseName), '', '')
      if (self.verbose):
        print 'INFO: Generating document with ignore conditions'
    else:
      self.docbook.writeHeader('MPS Database', info[2], info[3])

    self.writeDatabaseInfo()

    link_node = None
    if (linkNode):
      link_nodes = self.session.query(models.LinkNode).all()
      link_node = filter (lambda x : x.get_name() == linkNode, link_nodes)
      if (not link_node):
        print 'ERROR: link node "{}" not found'.format(linkNode)
        exit(-1)
      link_node=link_node[0]
    
    if (not self.cards_only and 
        not self.devices_only and 
        not self.checkout_only and
        not self.ignore_only and
        linkNode==None):
      self.writeBeamDestinations()

      self.writePowerClasses()

    if (self.cards_only or
        (not self.devices_only and
         not self.checkout_only and
         not self.ignore_only)):
      self.writeLinkNodes(link_node)

      self.writeCrates(link_node)

      if (not self.general_only):
        self.writeAppCards(link_node)

    if ((not self.cards_only or
         self.devices_only or
         self.checkout_only) and
        not self.ignore_only and
        not self.general_only):
      self.writeDevices(link_node)

      if (not link_node or 
          self.ignore_only): 
        self.writeIgnoreLogic()

    self.docbook.writeFooter()

    suffix=''
#    if (self.cards_only):
#      suffix='cards'
#    elif (self.devices_only):
#      suffix='devices'
#    elif (self.checkout_only):
#      suffix='checkout'
    self.docbook.exportHtml(suffix)
    self.docbook.exportPdf(suffix)

# --- Main ---

parser = argparse.ArgumentParser(description='Generate documentation from the MPS database')
parser.add_argument('database', metavar='db', type=file, nargs=1,
                    help='database file name (e.g. mps_gun.db)')
parser.add_argument('--output', metavar='output', type=str, nargs='?', 
                    help='directory where the documentation is generated')
parser.add_argument('--ignore-only', dest='ignore_only', action='store_true', default=False,
                    help="Generate documentation for the ignore logic only")
parser.add_argument('--general-only', dest='general_only', action='store_true', default=False,
                    help="Generate documentation about crates and link nodes, but not individual inputs")
parser.add_argument('--link-nodes-only', dest='link_nodes_only', action='store_true', default=False,
                    help="Generate documentation for each link node")
parser.add_argument('-v', action='store_true', default=False,
                    dest='verbose', help='Verbose output')
parser.add_argument('--ln', metavar='link_node_name', type=str, nargs='?',
                    help='generate documentation the specified link node only (sioc name)')

args = parser.parse_args()

output_dir = './'
if args.output:
  output_dir = args.output
  if (not os.path.isdir(output_dir)):
    print 'ERROR: Invalid output directory {0}'.format(output_dir)
    exit(-1)

e = Exporter(args.database[0].name, #args.checkout, cards_only, devices_only, checkout_only,
             args.general_only, args.ignore_only, args.verbose)
#split('/')[len(name2.split('/'))-1].split('.')[0]
doc_name = args.database[0].name.split('/')[len(args.database[0].name.split('/'))-1].split('.')[0]
#e.exportDocBook('{0}.xml'.format(args.database[0].name.split('.')[0]),
#                '{0}.txt'.format(args.database[0].name.split('.')[0]))

if (args.ln):
  fileName = '{0}/{1}.xml'.format(output_dir, args.ln)
  fileNameTxt = '{0}/{1}.txt'.format(output_dir, args.ln)
elif (args.ignore_only):
  fileName = '{0}/{1}-ignore.xml'.format(output_dir, doc_name)
  fileNameTxt = '{0}/{1}-ignore.txt'.format(output_dir, doc_name)
elif (args.general_only):
  fileName = '{0}/{1}-general.xml'.format(output_dir, doc_name)
  fileNameTxt = '{0}/{1}-general.txt'.format(output_dir, doc_name)
elif (args.link_nodes_only):
  e.exportDocBookLinkNodes(output_dir, doc_name)
  exit(0)
else:
  fileName = '{0}/{1}.xml'.format(output_dir, doc_name)
  fileNameTxt = '{0}/{1}.txt'.format(output_dir, doc_name)

e.exportDocBook(fileName, fileNameTxt, doc_name, args.ln)

