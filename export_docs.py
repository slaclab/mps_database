#!/usr/bin/env python

from mps_config import MPSConfig, models
import os
import sys
import argparse
import subprocess
import time
from mps_names import MpsName

class Exporter:
  databaseFileName=""
  mpsName=0
  session=0
  f=0
  tableHeaderColor='<?dbhtml bgcolor="#EE6060" ?><?dbfo bgcolor="#EE6060" ?>'
  tableRowColor=  ['<?dbhtml bgcolor="#EEEEEE" ?><?dbfo bgcolor="#EEEEEE" ?>',
                   '<?dbhtml bgcolor="#DDDDDD" ?><?dbfo bgcolor="#DDDDDD" ?>']
  siocPv='SIOC:SYS0:MP01'

  def __init__(self, dbFileName):
    self.databaseFileName = dbFileName
    mps = MPSConfig(args.database[0].name)
    self.session = mps.session
    self.mpsName = MpsName(self.session)
  
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

  def writeHeader(self):
    info = self.getAuthor()
    
    self.f.write('<article xmlns="http://docbook.org/ns/docbook" version="5.0">\n')
    self.f.write('\n')
    self.f.write('<info>\n')
    self.f.write('   <title>MpsDatabase</title>\n')
    self.f.write('   <author>\n')
    self.f.write('     <firstname>{0}</firstname><surname>{1}</surname>\n'.format(info[2], info[3]))
    self.f.write('   </author>\n')
    self.f.write('</info>\n')

    self.f.write('<section><title>Database Information</title>\n')

    self.f.write('<table>\n')
    self.f.write('<title>Database Information</title>\n')
    self.f.write('<tgroup cols=\'2\' align=\'left\' colsep=\'2\' rowsep=\'2\'>\n')
    self.f.write('<colspec colname=\'c1\' colwidth="0.5*"/>')
    self.f.write('<colspec colname=\'c2\'/>')
    self.f.write('<tbody>\n')
    
    rowIndex = 0
    self.f.write('<row>{0}\n'.format(self.tableRowColor[rowIndex%2]))
    rowIndex=rowIndex+1
    self.f.write('  <entry>Generated on</entry>\n')
    self.f.write('  <entry>{0}</entry>\n'.format(time.asctime(time.localtime(time.time()))))
    self.f.write('</row>\n')

    self.f.write('<row>{0}\n'.format(self.tableRowColor[rowIndex%2]))
    rowIndex=rowIndex+1
    self.f.write('  <entry>Author</entry>\n')
    self.f.write('  <entry>{0}, {1}</entry>\n'.format(info[3], info[2]))
    self.f.write('</row>\n')

    self.f.write('<row>{0}\n'.format(self.tableRowColor[rowIndex%2]))
    rowIndex=rowIndex+1
    self.f.write('  <entry>E-mail</entry>\n')
    self.f.write('  <entry>{0}</entry>\n'.format(info[1]))
    self.f.write('</row>\n')

    self.f.write('<row>{0}\n'.format(self.tableRowColor[rowIndex%2]))
    rowIndex=rowIndex+1
    self.f.write('  <entry>Username</entry>\n')
    self.f.write('  <entry>{0}</entry>\n'.format(info[0]))
    self.f.write('</row>\n')

    self.f.write('<row>{0}\n'.format(self.tableRowColor[rowIndex%2]))
    rowIndex=rowIndex+1
    self.f.write('  <entry>Database source</entry>\n')
    self.f.write('  <entry>{0}</entry>\n'.format(self.databaseFileName))
    self.f.write('</row>\n')

    cmd = "md5sum {0}".format(self.databaseFileName)
    process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
    md5sum_output, error = process.communicate()
    
    md5sum_tokens = md5sum_output.split()

    self.f.write('<row>{0}\n'.format(self.tableRowColor[rowIndex%2]))
    rowIndex=rowIndex+1
    self.f.write('  <entry>Database file MD5SUM</entry>\n')
    self.f.write('  <entry>{0}</entry>\n'.format(md5sum_tokens[0].strip()))
    self.f.write('</row>\n')

    self.f.write('</tbody>\n')
    self.f.write('</tgroup>\n')
    self.f.write('</table>\n')
    self.f.write('</section>\n')


  def writeMitigationTableHeader(self):
#    self.f.write('  <entry>Fault Name</entry>\n')
    mitDevices={}
    mitigationDevices = self.session.query(models.MitigationDevice).\
        order_by(models.MitigationDevice.destination_mask.desc())
    for mit in mitigationDevices:
      mitDevices[mit.name] = '-'
      self.f.write('  <entry>{0}</entry>\n'.format(mit.name))

    return mitDevices

  def writeMitigationTableRows(self, faultName, mitigationDevices):
#    self.f.write('  <entry>{0}</entry>\n'.format(faultName))
    for key in mitigationDevices:
      self.f.write('  <entry>{0}</entry>\n'.format(mitigationDevices[key]))

  def writeDigitalFault(self, fault, device):
    channelName = []
    channelCrateId = []
    channelCrate = []
    channelSlot = []
    channelNumber = []
    channelPv = []

    num_bits = 0

    for ddi in device.inputs:
      channel = self.session.query(models.DigitalChannel).\
          filter(models.DigitalChannel.id==ddi.channel_id).one()
      card = self.session.query(models.ApplicationCard).\
          filter(models.ApplicationCard.id==channel.card_id).one()
      crate = self.session.query(models.Crate).\
          filter(models.Crate.id==card.crate_id).one()
      num_bits = num_bits + 1

      channelName.append(channel.name)
      channelCrateId.append(crate.id)
      channelCrate.append(crate.location + crate.rack + '-' + str(crate.elevation))
      channelSlot.append(str(card.slot_number))
      channelNumber.append(str(channel.number))
      channelPv.append(self.mpsName.getDeviceInputName(ddi) + "_MPSC")

    numMitDevices = self.session.query(models.MitigationDevice).count()

    # Fault Table
    table_name = '{0} Fault States'.format(fault.name)
    self.f.write('<table id="fault_state_table_{0}" xreflabel="{1}">\n'.format(fault.id, table_name))
    self.f.write('<title>{0}</title>\n'.format(table_name))
    self.f.write('<tgroup cols=\'{0}\' align=\'left\' colsep=\'2\' rowsep=\'2\'>\n'.format(num_bits+numMitDevices+1))

    for b in range (0, num_bits):
      self.f.write('<colspec colname=\'b{0}\' colwidth="0.05*"/>'.format(b))

    self.f.write('<colspec colname=\'f1\' colwidth="0.25*"/>')

    for d in range (0, numMitDevices):
      self.f.write('<colspec colname=\'m{0}\' colwidth="0.10*"/>'.format(d))

    self.f.write('<thead>\n')
    self.f.write('<row>{0}\n'.format(self.tableHeaderColor))
    var = 'A'
    for b in range(0, num_bits):
      self.f.write('  <entry>{0}</entry>\n'.format(var))
      var = chr(ord(var) + 1)
    self.f.write('  <entry>Fault Name</entry>\n')
    mitDevices = self.writeMitigationTableHeader()
    self.f.write('</row>\n')
    self.f.write('</thead>\n')
    self.f.write('<tbody>\n')

    rowIndex = 0
    for state in fault.states:
      self.f.write('<row>{0}\n'.format(self.tableRowColor[rowIndex%2]))
      rowIndex=rowIndex+1
      deviceState = self.session.query(models.DeviceState).\
          filter(models.DeviceState.id==state.device_state_id).one()

      bits = []
      maskBits = []
      value = deviceState.value
      mask = deviceState.mask
      for b in range(0, num_bits):
        bits.append(value & 1)
        maskBits.append(mask & 1)
        value = (value >> 1)
        mask = (mask >> 1)
        if (maskBits[b] == 0):
          input_value = "-"
        else:
          input_value = bits[b]
          if (state.default == True):
            input_value = "default"

          for c in state.allowed_classes:
            beamClass = self.session.query(models.BeamClass).\
                filter(models.BeamClass.id==c.beam_class_id).one()
            mitigationDevice = self.session.query(models.MitigationDevice).\
                filter(models.MitigationDevice.id==c.mitigation_device_id).one()
            
            mitDevices[mitigationDevice.name] = beamClass.name
          # end for

          self.f.write('  <entry>{0}</entry>\n'.format(input_value))
    
      self.f.write('  <entry>{0}</entry>\n'.format(deviceState.name))
      self.writeMitigationTableRows(deviceState.name, mitDevices)
      self.f.write('</row>\n')

    self.f.write('</tbody>\n')
    self.f.write('</tgroup>\n')
    self.f.write('</table>\n')

    # Fault Inputs
    table_name = '{0} Fault Inputs'.format(fault.name)
    self.f.write('<table id="fault_input_table_{0}" xreflabel="{1}">\n'.format(fault.id, table_name))
    self.f.write('<title>{0}</title>\n'.format(table_name))
    self.f.write('<tgroup cols=\'{0}\' align=\'left\' colsep=\'2\' rowsep=\'2\'>\n'.format(6))
    self.f.write('<colspec colname=\'c1\' colwidth="0.08*"/>')
    self.f.write('<colspec colname=\'c2\' colwidth="0.25*"/>')
    self.f.write('<colspec colname=\'c3\' colwidth="0.20*"/>')
    self.f.write('<colspec colname=\'c4\' colwidth="0.08*"/>')
    self.f.write('<colspec colname=\'c5\' colwidth="0.08*"/>')
    self.f.write('<colspec colname=\'c6\' colwidth="0.50*"/>')
    self.f.write('<thead>\n')
    self.f.write('<row>{0}\n'.format(self.tableHeaderColor))
    self.f.write('  <entry>Input</entry>\n')
    self.f.write('  <entry>Name</entry>\n')
    self.f.write('  <entry>Crate</entry>\n')
    self.f.write('  <entry>Slot</entry>\n')
    self.f.write('  <entry>Ch #</entry>\n')
    self.f.write('  <entry>PV</entry>\n')
    self.f.write('</row>\n')
    self.f.write('</thead>\n')
    self.f.write('<tbody>\n')
    
    var = 'A'
    rowIndex = 0
    for b in range(0, num_bits):
      self.f.write('<row>{0}\n'.format(self.tableRowColor[rowIndex%2]))
      rowIndex=rowIndex+1
      self.f.write('  <entry>{0}</entry>\n'.format(var))
      self.f.write('  <entry>{0}</entry>\n'.format(channelName[b]))
      self.f.write('  <entry><link linkend=\'crate.{0}\'>{1}</link></entry>\n'.format(channelCrateId[b], channelCrate[b]))
      self.f.write('  <entry>{0}</entry>\n'.format(channelSlot[b]))
      self.f.write('  <entry>{0}</entry>\n'.format(channelNumber[b]))
      self.f.write('  <entry>{0}</entry>\n'.format(channelPv[b]))
      self.f.write('</row>\n')
      var = chr(ord(var) + 1)

    self.f.write('</tbody>\n')
    self.f.write('</tgroup>\n')
    self.f.write('</table>\n')

    # Fault Checkout Table

# <sect1 id="install_packages" xreflabel="installing the needed packages"> 
# Later you can refer to that section using::
# See <xref linkend="install_packages"/> for more information. 


    self.f.write('<section>\n')
    self.f.write('<title>{0} Checkout</title>\n'.format(fault.name))
    self.f.write('<para>Check all fault input combinations listed in tables "<xref linkend="fault_state_table_{0}"/>" and "<xref linkend="fault_input_table_{0}"/>". For each fault state verify the inputs and make sure the fault PV is in the faulted state (Fault PV in table "<xref linkend="device_faults_table_{1}"/>"). Write down the power class for each mitigation device. The power levels must match the ones listed in the "<xref linkend="fault_state_table_{0}"/>" table.\n'.format(fault.id, device.id))
    self.f.write('</para>\n')

    self.f.write('<table>\n')
    self.f.write('<title>{0} Fault Checkout</title>\n'.format(fault.name))
    self.f.write('<tgroup cols=\'{0}\' align=\'left\' colsep=\'2\' rowsep=\'2\'>\n'.format(numMitDevices+2))
    self.f.write('<colspec colname=\'fault1\' colwidth="0.10*"/>')
    self.f.write('<colspec colname=\'fault2\' colwidth="0.50*"/>')
    for i in range(0, numMitDevices):
      self.f.write('<colspec colname=\'m{0}\' colwidth="0.10*"/>'.format(i))
    self.f.write('<thead>\n')
    self.f.write('<row>{0}\n'.format(self.tableHeaderColor))
    self.f.write('  <entry namest="fault1" nameend="fault2">Fault Name</entry>\n')
    mitDevices = self.writeMitigationTableHeader()
    self.f.write('</row>\n')
    self.f.write('</thead>\n')
    self.f.write('<tbody>\n')

    rowIndex = 0
    for state in fault.states:
      self.f.write('<row>{0}\n'.format(self.tableRowColor[rowIndex%2]))
      rowIndex=rowIndex+1
      deviceState = self.session.query(models.DeviceState).\
          filter(models.DeviceState.id==state.device_state_id).one()

#      self.f.write('  <entry><mediaobject><imageobject condition="print"><imagedata contentwidth="0.5cm" fileref="checkbox.png"/></imageobject><imageobject condition="web"><imagedata fileref="http://www.slac.stanford.edu/~lpiccoli/checkbox.png"/></imageobject></mediaobject></entry>\n')
      self.f.write('  <entry><mediaobject><imageobject condition="print"><imagedata contentwidth="0.5cm" fileref="checkbox.png"/></imageobject><imageobject condition="web"><imagedata fileref="http://www.slac.stanford.edu/~lpiccoli/checkbox.png"/></imageobject></mediaobject></entry>\n')
      self.f.write('  <entry>{0}</entry>\n'.format(deviceState.name))    
      for key in mitDevices:
        self.f.write('  <entry><mediaobject><imageobject condition="print"><imagedata contentwidth="0.5cm" fileref="checkbox.png"/></imageobject><imageobject condition="web"><imagedata fileref="http://www.slac.stanford.edu/~lpiccoli/checkbox.png"/></imageobject></mediaobject></entry>\n')
      self.f.write('</row>\n')

    self.f.write('</tbody>\n')
    self.f.write('</tgroup>\n')
    self.f.write('</table>\n')
    self.f.write('</section>\n')

  def writeAnalogFault(self, fault, device):
    num_bits = 0

    channelName = []
    channelCrate = []
    channelSlot = []
    channelNumber = []
    channelMask = []
    channelPv = []

    integratorShift = 0
    if ("X" in fault.name or "I0" in fault.name or "CHARGE" in fault.name):
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

      channelName.append(deviceState.name)
      channelCrate.append(str(crate.number))
      channelSlot.append(str(card.slot_number))
      channelNumber.append(str(channel.number))
      channelMask.append(str(hex((deviceState.mask >> integratorShift) & 0xFF)))
      channelPv.append(self.mpsName.getAnalogDeviceName(device) + ":" + state.device_state.name)
      
    self.f.write('<para>Table "<xref linkend="fault_states.{1}"/>" lists the {0} fault input bits for the {2} device. MPS supports up to eight comparators for {0}, this database version {3} \n'.format(fault.name, fault.id, device.name, len(fault.states)))
    self.f.write('</para>\n')

    # Fault States
    max_bits = 8 # max number of analog thresholds
    numMitDevices = self.session.query(models.MitigationDevice).count()
    table_name = '{0} Fault States'.format(fault.name)
    self.f.write('<table id="fault_states.{0}" xreflabel="{1}">\n'.format(fault.id, table_name))
    self.f.write('<title>{0}</title>\n'.format(table_name))
    self.f.write('<tgroup cols=\'{0}\' align=\'left\' colsep=\'2\' rowsep=\'2\'>\n'.format(max_bits+numMitDevices+1))
    for b in range(0, max_bits):
      self.f.write('<colspec colname=\'b1\' colwidth="0.05*"/>'.format(b))
    self.f.write('<colspec colname=\'f2\' colwidth="0.30*"/>')
    for m in range(0, numMitDevices):
      self.f.write('<colspec colname=\'m{0}\' colwidth="0.20*"/>')
    self.f.write('<thead>\n')
    self.f.write('<row>{0}\n'.format(self.tableHeaderColor))
#    var = 'A'
    var = '7'
    for b in range(0, max_bits):
      self.f.write('  <entry>{0}</entry>\n'.format(var))
#      var = chr(ord(var) + 1)
      var = chr(ord(var) - 1)
    self.f.write('  <entry>Fault Name</entry>\n')
    mitDevices = self.writeMitigationTableHeader()
    self.f.write('</row>\n')
    self.f.write('</thead>\n')
    self.f.write('<tbody>\n')

    rowIndex = 0
    for state in fault.states:
      self.f.write('<row>{0}\n'.format(self.tableRowColor[rowIndex%2]))
      rowIndex=rowIndex+1

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
          self.f.write('  <entry>1</entry>\n')
        else:
          self.f.write('  <entry>-</entry>\n')
        v = (v >> 1)

        for c in state.allowed_classes:
          beamClass = self.session.query(models.BeamClass).filter(models.BeamClass.id==c.beam_class_id).one()
          mitigationDevice = self.session.query(models.MitigationDevice).filter(models.MitigationDevice.id==c.mitigation_device_id).one()
          mitDevices[mitigationDevice.name] = beamClass.name
        # end for c
      # end for b
      self.f.write('  <entry>{0}</entry>\n'.format(fault.name))
      self.writeMitigationTableRows(fault.name, mitDevices)
      self.f.write('</row>\n')
    # end for state
    self.f.write('</tbody>\n')
    self.f.write('</tgroup>\n')
    self.f.write('</table>\n')

    # Fault Threshold Input Bits
    self.f.write('<table>\n')
    self.f.write('<title>{0} Fault Inputs (thresholds)</title>\n'.format(fault.name))
    self.f.write('<tgroup cols=\'{0}\' align=\'left\' colsep=\'2\' rowsep=\'2\'>\n'.format(7))
    self.f.write('<colspec colname=\'c1\' colwidth="0.08*"/>')
    self.f.write('<colspec colname=\'c2\' colwidth="0.25*"/>')
    self.f.write('<colspec colname=\'c3\' colwidth="0.15*"/>')
    self.f.write('<colspec colname=\'c4\' colwidth="0.15*"/>')
    self.f.write('<colspec colname=\'c5\' colwidth="0.15*"/>')
    self.f.write('<colspec colname=\'c6\' colwidth="0.50*"/>')
    self.f.write('<thead>\n')
    self.f.write('<row>{0}\n'.format(self.tableHeaderColor))
    self.f.write('  <entry>Bit</entry>\n')
    self.f.write('  <entry>Name</entry>\n')
    self.f.write('  <entry>Crate</entry>\n')
    self.f.write('  <entry>Slot</entry>\n')
    self.f.write('  <entry>Ch #</entry>\n')
    self.f.write('  <entry>Mask</entry>\n')
    self.f.write('  <entry>PV</entry>\n')
    self.f.write('</row>\n')
    self.f.write('</thead>\n')
    self.f.write('<tbody>\n')

    var = '0'
    rowIndex = 0
    for b in range(0, num_bits):
      self.f.write('<row>{0}\n'.format(self.tableRowColor[rowIndex%2]))
      rowIndex=rowIndex+1
      self.f.write('  <entry>{0}</entry>\n'.format(var))
      self.f.write('  <entry>{0}</entry>\n'.format(channelName[b]))
      self.f.write('  <entry>{0}</entry>\n'.format(channelCrate[b]))
      self.f.write('  <entry>{0}</entry>\n'.format(channelSlot[b]))
      self.f.write('  <entry>{0}</entry>\n'.format(channelNumber[b]))
      self.f.write('  <entry>{0}</entry>\n'.format(channelMask[b]))
      self.f.write('  <entry>{0}_MPSC</entry>\n'.format(channelPv[b]))
      self.f.write('</row>\n')
      var = chr(ord(var) + 1)

    self.f.write('</tbody>\n')
    self.f.write('</tgroup>\n')
    self.f.write('</table>\n')

    self.f.write('<para>Check all {0} faults caused by inputs crossing the high and low thresholds for all comparators (there are up to eight comparators for each fault (input bits A through H). Only the fault states listed on "<xref linkend="fault_states.{1}"/>" table are defined in this database.\n'.format(fault.name, fault.id))
    self.f.write('</para>\n')

    self.f.write('<para>Table "<xref linkend="fault_checkout.{0}"/>" lists the PVs that should be changed to test the faults. Set the LOLO/HIHI PVs with values that cause MPS mitigation actions and write down the power classes.</para>\n'.format(fault.id))

    # Fault Checkout Table
    table_name = '{0} Fault Checkout'.format(fault.name)
    self.f.write('<table id="fault_checkout.{0}" xreflabel="{1}">\n'.format(fault.id, table_name))
    self.f.write('<title>{0}</title>\n'.format(table_name))
    self.f.write('<tgroup cols=\'{0}\' align=\'left\' colsep=\'2\' rowsep=\'2\'>\n'.format(numMitDevices+4))
    self.f.write('<colspec colname=\'fault1\' colwidth="0.12*"/>')
    self.f.write('<colspec colname=\'fault2\' colwidth="0.35*"/>')
    self.f.write('<colspec colname=\'threshold1\' colwidth="0.65*"/>')
    self.f.write('<colspec colname=\'threshold2\' colwidth="0.25*"/>')
    for m in range(0, numMitDevices):
      self.f.write('<colspec colname=\'m{0}\' colwidth="0.15*"/>')
    self.f.write('<thead>\n')
    self.f.write('<row>{0}\n'.format(self.tableHeaderColor))
    self.f.write('  <entry namest="fault1" nameend="fault2">Fault</entry>\n')
    self.f.write('  <entry namest="threshold1" nameend="threshold2">Threshold (PV, Value)</entry>\n')
    mitDevices = self.writeMitigationTableHeader()
    self.f.write('</row>\n')
    self.f.write('</thead>\n')
    self.f.write('<tbody>\n')

    rowIndex = 0
    for state in fault.states:
      deviceState = self.session.query(models.DeviceState).\
          filter(models.DeviceState.id==state.device_state_id).one()

      thresholdPv = self.mpsName.getAnalogDeviceName(device) + ":" + deviceState.name

      # Low threshold
      self.f.write('<row>{0}\n'.format(self.tableRowColor[rowIndex%2]))
      rowIndex=rowIndex+1
#      self.f.write('  <entry>___</entry>\n')
      self.f.write('  <entry><mediaobject><imageobject condition="print"><imagedata contentwidth="0.5cm" fileref="checkbox.png"/></imageobject><imageobject condition="web"><imagedata fileref="http://www.slac.stanford.edu/~lpiccoli/checkbox.png"/></imageobject></mediaobject></entry>\n')
      self.f.write('  <entry>{0} (Low)</entry>\n'.format(deviceState.name))    
      self.f.write('  <entry>{0}_LOLO</entry>\n'.format(thresholdPv))
#      self.f.write('  <entry>_____</entry>\n')
      self.f.write('  <entry><mediaobject><imageobject condition="print"><imagedata contentdepth="0.5cm" fileref="checkbox-long.png"/></imageobject><imageobject condition="web"><imagedata fileref="http://www.slac.stanford.edu/~lpiccoli/checkbox-long.png"/></imageobject></mediaobject></entry>\n')
      for key in mitDevices:
#        self.f.write('  <entry>_____</entry>\n')
        self.f.write('  <entry><mediaobject><imageobject condition="print"><imagedata contentwidth="0.5cm" fileref="checkbox.png"/></imageobject><imageobject condition="web"><imagedata fileref="http://www.slac.stanford.edu/~lpiccoli/checkbox.png"/></imageobject></mediaobject></entry>\n')
      self.f.write('</row>\n')

      # High threshold
      self.f.write('<row>{0}\n'.format(self.tableRowColor[rowIndex%2]))
      rowIndex=rowIndex+1
#      self.f.write('  <entry>_____</entry>\n')
      self.f.write('  <entry><mediaobject><imageobject condition="print"><imagedata contentwidth="0.5cm" fileref="checkbox.png"/></imageobject><imageobject condition="web"><imagedata fileref="http://www.slac.stanford.edu/~lpiccoli/checkbox.png"/></imageobject></mediaobject></entry>\n')
      self.f.write('  <entry>{0} (High)</entry>\n'.format(deviceState.name))    
      self.f.write('  <entry>{0}_HIHI</entry>\n'.format(thresholdPv))
#      self.f.write('  <entry>_____</entry>\n')
      self.f.write('  <entry><mediaobject><imageobject condition="print"><imagedata contentdepth="0.5cm" fileref="checkbox-long.png"/></imageobject><imageobject condition="web"><imagedata fileref="http://www.slac.stanford.edu/~lpiccoli/checkbox-long.png"/></imageobject></mediaobject></entry>\n')
      for key in mitDevices:
#        self.f.write('  <entry>_____</entry>\n')
        self.f.write('  <entry><mediaobject><imageobject condition="print"><imagedata contentwidth="0.5cm" fileref="checkbox.png"/></imageobject><imageobject condition="web"><imagedata fileref="http://www.slac.stanford.edu/~lpiccoli/checkbox.png"/></imageobject></mediaobject></entry>\n')
      self.f.write('</row>\n')

    self.f.write('</tbody>\n')
    self.f.write('</tgroup>\n')
    self.f.write('</table>\n')


  def writeFault(self, fault, device):
    self.f.write('<section>\n')
    self.f.write('<anchor id=\'fault.{0}\'></anchor>\n'.format(fault.id))
    self.f.write('<title>{0} Fault</title>\n'.format(fault.name))
    
    for inp in fault.inputs:
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
          self.writeAnalogFault(fault, analogDevice)
        except:
          print("ERROR: Can't find device for fault[{0}]:desc[{1}], device Id: {2}, fault_input id: {3}".\
                  format(fault.name, fault.description, inp.device_id, inp.id))
          exit(-1)

    self.f.write('</section>\n')

  def writeDeviceFaults(self, device):
    self.f.write('<section>\n')
    self.f.write('<title>{0} Faults</title>\n'.format(device.name))

#    self.f.write('<table>\n')
    table_name = '{0} Faults'.format(device.name)
    self.f.write('<table id="device_faults_table_{0}" xreflabel="{1}">\n'.format(device.id, table_name))
    self.f.write('<title>{0}</title>\n'.format(table_name))
    self.f.write('<tgroup cols=\'3\' align=\'left\' colsep=\'1\' rowsep=\'1\'>\n')
    self.f.write('<colspec colname=\'c1\' colwidth="0.35*"/>')
    self.f.write('<colspec colname=\'c2\'/>')
    self.f.write('<colspec colname=\'c3\'/>')
    self.f.write('<thead>\n')
    self.f.write('<row>{0}\n'.format(self.tableHeaderColor))
    self.f.write('  <entry>Name</entry>\n')
    self.f.write('  <entry>Description</entry>\n')
    self.f.write('  <entry>Fault PV</entry>\n')
    self.f.write('</row>\n')
    self.f.write('</thead>\n')
    self.f.write('<tbody>\n')

    rowIndex = 0
    for fault_input in device.fault_outputs:
      fault = self.session.query(models.Fault).filter(models.Fault.id==fault_input.fault_id).one()
      self.f.write('<row>{0}\n'.format(self.tableRowColor[rowIndex%2]))
      rowIndex=rowIndex+1
      self.f.write('  <entry><link linkend=\'fault.{0}\'>{1}</link></entry>\n'.format(fault.id, fault.name))
      self.f.write('  <entry>{0}</entry>\n'.format(fault.description))
      self.f.write('  <entry>{0}</entry>\n'.format(self.mpsName.getFaultName(fault)))
      self.f.write('</row>\n')

    self.f.write('</tbody>\n')
    self.f.write('</tgroup>\n')
    self.f.write('</table>\n')

    for fault_input in device.fault_outputs:
      fault = self.session.query(models.Fault).filter(models.Fault.id==fault_input.fault_id).one()
      self.writeFault(fault, device)
    self.f.write('</section>\n')

  def writeDeviceInfo(self, device):
    keys = ['name', 'description', 'area', 'position']
    self.f.write('<section>\n')
    self.f.write('<anchor id=\'device.{0}\'></anchor>\n'.format(device.id))
    self.f.write('<title>{0}</title>\n'.format(device.name))
    self.f.write('<table>\n')
    self.f.write('<title>{0} properties</title>\n'.format(device.name))
    self.f.write('<tgroup cols=\'2\' align=\'left\' colsep=\'1\' rowsep=\'1\'>\n')
    self.f.write('<colspec colname=\'c1\' colwidth="0.25*"/>')
    self.f.write('<colspec colname=\'c2\'/>')
    self.f.write('<thead>\n')
    self.f.write('<row>{0}\n'.format(self.tableHeaderColor))
    self.f.write('  <entry>Property</entry>\n')
    self.f.write('  <entry>Value</entry>\n')
    self.f.write('</row>\n')
    self.f.write('</thead>\n')
    self.f.write('<tbody>\n')

    rowIndex = 0
    for k in keys:
      if not k.startswith('_'):
        self.f.write('<row>{0}\n'.format(self.tableRowColor[rowIndex%2]))
        rowIndex=rowIndex+1
        self.f.write('  <entry>{0}</entry>\n'.format(k))
        self.f.write('  <entry>{0}</entry>\n'.format(getattr(device, k)))
        self.f.write('</row>\n')
    # end for k

    self.f.write('<row>{0}\n'.format(self.tableRowColor[rowIndex%2]))
    rowIndex=rowIndex+1
    self.f.write('  <entry>type</entry>\n'.format(k))
    dt = self.session.query(models.DeviceType).filter(models.DeviceType.id==device.device_type_id).one()
    self.f.write('  <entry>{0}</entry>\n'.format(dt.name))
    self.f.write('</row>\n')
    
    self.f.write('</tbody>\n')
    self.f.write('</tgroup>\n')
    self.f.write('</table>\n')

    self.writeDeviceFaults(device)
    
    self.f.write('</section>\n')

  def writeDigitalCheckoutTable(self, card_name, channels):
    self.f.write('<section>\n')
    self.f.write('<title>{0} Checkout</title>\n'.format(card_name))
    self.f.write('<para>For every signal in the checkout table change it using the respective subsystem (e.g. Profile Monitor for inserting/removing screen) and verify if the input state changes. Check mark the states making sure they reflect the device state.\n')
    self.f.write('</para>\n')
    self.f.write('<table>\n')
    self.f.write('<title>Checkout table for digital inputs</title>\n')
    self.f.write('<tgroup cols=\'6\' align=\'left\' colsep=\'1\' rowsep=\'1\'>\n')
    self.f.write('<colspec colname=\'channel\' colwidth="0.15*"/>')
    self.f.write('<colspec colname=\'zero1\' colwidth="0.15*"/>')
    self.f.write('<colspec colname=\'zero2\' colwidth="0.40*"/>')
    self.f.write('<colspec colname=\'one1\' colwidth="0.15*"/>')
    self.f.write('<colspec colname=\'one2\' colwidth="0.40*"/>')
    self.f.write('<colspec colname=\'pv\'/>')
    self.f.write('<thead>\n')
    self.f.write('<row>{0}\n'.format(self.tableHeaderColor))
    self.f.write('  <entry>Ch #</entry>\n')
    self.f.write('  <entry namest="zero1" nameend="zero2">Low State (0V)</entry>\n')
    self.f.write('  <entry namest="one1" nameend="one2">High State (24V)</entry>\n')
    self.f.write('  <entry>PV</entry>\n')
    self.f.write('</row>\n')
    self.f.write('</thead>\n')
    self.f.write('<tbody>\n')

    rowIndex = 0
    for c in channels:
      ddi = self.session.query(models.DeviceInput).filter(models.DeviceInput.channel_id==c.id).one()
      device = self.session.query(models.Device).filter(models.Device.id==ddi.digital_device.id).one()

      self.f.write('<row>{0}\n'.format(self.tableRowColor[rowIndex%2]))
      rowIndex=rowIndex+1
      self.f.write('  <entry>{0}</entry>\n'.format(c.number))
      self.f.write('  <entry><mediaobject><imageobject condition="print"><imagedata contentwidth="0.5cm" fileref="checkbox.png"/></imageobject><imageobject condition="web"><imagedata fileref="http://www.slac.stanford.edu/~lpiccoli/checkbox.png"/></imageobject></mediaobject></entry>\n')
      self.f.write('  <entry>{0}</entry>\n'.format(c.z_name))
      self.f.write('  <entry><mediaobject><imageobject condition="print"><imagedata contentwidth="0.5cm" fileref="checkbox.png"/></imageobject><imageobject condition="web"><imagedata fileref="http://www.slac.stanford.edu/~lpiccoli/checkbox.png"/></imageobject></mediaobject></entry>\n')
      self.f.write('  <entry>{0}</entry>\n'.format(c.o_name))
      self.f.write('  <entry>{0}_MPSC</entry>\n'.format(self.mpsName.getDeviceInputName(ddi)))
      self.f.write('</row>\n')
    # end for c

    self.f.write('</tbody>\n')
    self.f.write('</tgroup>\n')
    self.f.write('</table>\n')
    self.f.write('</section>\n')

  def writeAppCard(self, card):
    self.f.write('<anchor id=\'card.{0}\'/>\n'.format(card.id))
    self.f.write('<section><title>{0}</title>\n'.format(card.name))

    crate = self.session.query(models.Crate).filter(models.Crate.id==card.crate_id).one()
    crate_name = crate.location + crate.rack + '-' + str(crate.elevation)

    keys = ['name', 'description', 'area', 'global_id', 'slot_number']

    self.f.write('<table>\n')
    self.f.write('<title>{0} properties</title>\n'.format(card.name))
    self.f.write('<tgroup cols=\'2\' align=\'left\' colsep=\'1\' rowsep=\'1\'>\n')
    self.f.write('<colspec colname=\'c1\' colwidth="0.25*"/>')
    self.f.write('<colspec colname=\'c2\'/>')
    self.f.write('<thead>\n')
    self.f.write('<row>{0}\n'.format(self.tableHeaderColor))
    self.f.write('  <entry>Property</entry>\n')
    self.f.write('  <entry>Value</entry>\n')
    self.f.write('</row>\n')
    self.f.write('</thead>\n')
    self.f.write('<tbody>\n')

    rowIndex = 0
    self.f.write('<row>{0}\n'.format(self.tableRowColor[rowIndex%2]))
    rowIndex=rowIndex+1
    self.f.write('  <entry>Crate</entry>\n')
    self.f.write('  <entry><link linkend=\'crate.{0}\'>{1}</link></entry>\n'.format(crate.id, crate_name))
    self.f.write('</row>\n')

    for k in keys:
      if not k.startswith('_'):
        self.f.write('<row>{0}\n'.format(self.tableRowColor[rowIndex%2]))
        rowIndex=rowIndex+1
        self.f.write('  <entry>{0}</entry>\n'.format(k))
        self.f.write('  <entry>{0}</entry>\n'.format(getattr(card, k)))
        self.f.write('</row>\n')
    # end for k

    self.f.write('</tbody>\n')
    self.f.write('</tgroup>\n')
    self.f.write('</table>\n')

    # Application Card Devices
    self.f.write('<table>\n')
    self.f.write('<title>{0} devices</title>\n'.format(card.name))
    self.f.write('<tgroup cols=\'2\' align=\'left\' colsep=\'1\' rowsep=\'1\'>\n')
    self.f.write('<colspec colname=\'c1\' colwidth="0.25*"/>')
    self.f.write('<colspec colname=\'c2\'/>')
    self.f.write('<thead>\n')
    self.f.write('<row>{0}\n'.format(self.tableHeaderColor))
    self.f.write('  <entry>Name</entry>\n')
    self.f.write('  <entry>Description</entry>\n')
    self.f.write('</row>\n')
    self.f.write('</thead>\n')
    self.f.write('<tbody>\n')
    
    rowIndex = 0
    for d in card.devices:
      self.f.write('<row>{0}\n'.format(self.tableRowColor[rowIndex%2]))
      rowIndex=rowIndex+1
      self.f.write('  <entry><link linkend=\'device.{0}\'>{1}</link></entry>\n'.format(d.id, d.name))
      self.f.write('  <entry>{0}</entry>\n'.format(d.description))
      self.f.write('</row>\n')
    # end for d

    self.f.write('</tbody>\n')
    self.f.write('</tgroup>\n')
    self.f.write('</table>\n')

    # Application Card Channels
    self.f.write('<table>\n')
    self.f.write('<title>{0} channels</title>\n'.format(card.name))
    self.f.write('<tgroup cols=\'3\' align=\'left\' colsep=\'1\' rowsep=\'1\'>\n')
    self.f.write('<colspec colname=\'c1\' colwidth="0.20*"/>')
    self.f.write('<colspec colname=\'c2\'/>')
    self.f.write('<colspec colname=\'c3\'/>')
    self.f.write('<thead>\n')
    self.f.write('<row>{0}\n'.format(self.tableHeaderColor))
    self.f.write('  <entry>Ch #</entry>\n')
    self.f.write('  <entry>Input Device</entry>\n')
    self.f.write('  <entry>Signal</entry>\n')
    self.f.write('</row>\n')
    self.f.write('</thead>\n')
    self.f.write('<tbody>\n')
    
    digital = True
    if (len(card.digital_channels) > 0):
      channels = card.digital_channels
    elif (len(card.analog_channels) > 0):
      channels = card.analog_channels
      digital = False
    else:
      print "ERROR"
      exit(-1)

    rowIndex = 0
    for c in channels:
      if digital:
        ddi = self.session.query(models.DeviceInput).filter(models.DeviceInput.channel_id==c.id).one()
        device = self.session.query(models.Device).filter(models.Device.id==ddi.digital_device.id).one()
        signal_name = c.name
      else:
        device = self.session.query(models.AnalogDevice).filter(models.AnalogDevice.channel_id==c.id).one()
        signal_name = c.name + ' thresholds'

      self.f.write('<row>{0}\n'.format(self.tableRowColor[rowIndex%2]))
      rowIndex=rowIndex+1
      self.f.write('  <entry>{0}</entry>\n'.format(c.number))
      self.f.write('  <entry>{0}</entry>\n'.format(device.name))
      self.f.write('  <entry>{0}</entry>\n'.format(signal_name))
      self.f.write('</row>\n')
    # end for c

    self.f.write('</tbody>\n')
    self.f.write('</tgroup>\n')
    self.f.write('</table>\n')

    if digital:
      self.writeDigitalCheckoutTable(card.name, channels)

    self.f.write('</section>\n')

  def writeAppCards(self):
    self.f.write('<section><title>Application Cards</title>\n')
    for card in self.session.query(models.ApplicationCard).all():
      self.writeAppCard(card)
    self.f.write('</section>\n')
    
  def writeCrate(self, crate):
    name = crate.location + crate.rack + '-' + str(crate.elevation)
    self.f.write('<anchor id=\'crate.{0}\'></anchor>\n'.format(crate.id))
    self.f.write('<section><title>{0}</title>\n'.format(name))

    # Application Cards
    self.f.write('<table>\n')
    self.f.write('<title>{0} cards</title>\n'.format(name))
    self.f.write('<tgroup cols=\'4\' align=\'left\' colsep=\'1\' rowsep=\'1\'>\n')
    self.f.write('<colspec colname=\'c1\' colwidth="0.15*"/>')
    self.f.write('<colspec colname=\'c2\'/>')
    self.f.write('<colspec colname=\'c3\' colwidth="0.20*"/>')
    self.f.write('<colspec colname=\'c4\'/>')
    self.f.write('<thead>\n')
    self.f.write('<row>{0}\n'.format(self.tableHeaderColor))
    self.f.write('  <entry>Slot #</entry>\n')
    self.f.write('  <entry>Application Card</entry>\n')
    self.f.write('  <entry>Global Id</entry>\n')
    self.f.write('  <entry>Card Description</entry>\n')
    self.f.write('</row>\n')
    self.f.write('</thead>\n')
    self.f.write('<tbody>\n')

    rowIndex = 0
    for card in crate.cards:
      self.f.write('<row>{0}\n'.format(self.tableRowColor[rowIndex%2]))
      rowIndex=rowIndex+1
      self.f.write('  <entry><link linkend=\'card.{0}\'>{1}</link></entry>\n'.format(card.id, card.slot_number))
      self.f.write('  <entry>{0}</entry>\n'.format(card.name))
      self.f.write('  <entry>{0}</entry>\n'.format(card.global_id))
      self.f.write('  <entry>{0}</entry>\n'.format(card.description))
      self.f.write('</row>\n')
    # end for d

    self.f.write('</tbody>\n')
    self.f.write('</tgroup>\n')
    self.f.write('</table>\n')

    self.f.write('</section>\n')

  def writeMitigationDevices(self):
    self.f.write('<section>\n')
    self.f.write('<title>Mitigation Devices</title>\n')

    # Mitigation Devices Table
    table_name = 'Mitigation Devices'
    self.f.write('<table id="mitigation_devices_table" xreflabel="{0}">\n'.format(table_name))
    self.f.write('<title>{0}</title>\n'.format(table_name))
    self.f.write('<tgroup cols=\'4\' align=\'left\' colsep=\'2\' rowsep=\'2\'>\n')
    self.f.write('<colspec colname=\'c1\' colwidth="0.20*"/>')
    self.f.write('<colspec colname=\'c2\' colwidth="0.35*"/>')
    self.f.write('<colspec colname=\'c3\' colwidth="0.15*"/>')
    self.f.write('<colspec colname=\'c4\' colwidth="0.55*"/>')
    self.f.write('<thead>\n')
    self.f.write('<row>{0}\n'.format(self.tableHeaderColor))
    self.f.write('  <entry>Name</entry>\n')
    self.f.write('  <entry>Description</entry>\n')
    self.f.write('  <entry>Mask</entry>\n')
    self.f.write('  <entry>PV</entry>\n')
    self.f.write('</row>\n')

    self.f.write('</thead>\n')
    self.f.write('<tbody>\n')
    rowIndex = 0
    for mitigation in self.session.query(models.MitigationDevice).all():
      self.f.write('<row>{0}\n'.format(self.tableRowColor[rowIndex%2]))
      rowIndex=rowIndex+1
      pvName = self.siocPv + ":" + mitigation.name + "_PC"
      self.f.write('  <entry>{0}</entry>\n'.format(mitigation.name))
      self.f.write('  <entry>{0}</entry>\n'.format(mitigation.description))
      self.f.write('  <entry>{0}</entry>\n'.format(str(hex(mitigation.destination_mask))))
      self.f.write('  <entry>{0}</entry>\n'.format(pvName))
      self.f.write('</row>\n')

      self.f.write('<row>{0}\n'.format(self.tableRowColor[rowIndex%2]))
      rowIndex=rowIndex+1
      pvName = self.siocPv + ":" + mitigation.name + "_FW_PC"
      self.f.write('  <entry></entry>\n')
      self.f.write('  <entry></entry>\n')
      self.f.write('  <entry></entry>\n')
      self.f.write('  <entry>{0}</entry>\n'.format(pvName))
      self.f.write('</row>\n')

      self.f.write('<row>{0}\n'.format(self.tableRowColor[rowIndex%2]))
      rowIndex=rowIndex+1
      pvName = self.siocPv + ":" + mitigation.name + "_SW_PC"
      self.f.write('  <entry></entry>\n')
      self.f.write('  <entry></entry>\n')
      self.f.write('  <entry></entry>\n')
      self.f.write('  <entry>{0}</entry>\n'.format(pvName))
      self.f.write('</row>\n')


    self.f.write('</tbody>\n')
    self.f.write('</tgroup>\n')
    self.f.write('</table>\n')
    self.f.write('</section>\n')
    
  def writePowerClasses(self):
    self.f.write('<section>\n')
    self.f.write('<title>Beam Power Classes</title>\n')

    # Beam Power Classes Table
    table_name = 'Beam Power Classes'
    self.f.write('<table id="power_classes_table" xreflabel="{0}">\n'.format(table_name))
    self.f.write('<title>{0}</title>\n'.format(table_name))
    self.f.write('<tgroup cols=\'6\' align=\'left\' colsep=\'2\' rowsep=\'2\'>\n')
    self.f.write('<colspec colname=\'c1\' colwidth="0.05*"/>')
    self.f.write('<colspec colname=\'c2\' colwidth="0.20*"/>')
    self.f.write('<colspec colname=\'c3\' colwidth="0.25*"/>')
    self.f.write('<colspec colname=\'c4\' colwidth="0.20*"/>')
    self.f.write('<colspec colname=\'c5\' colwidth="0.20*"/>')
    self.f.write('<colspec colname=\'c6\' colwidth="0.20*"/>')
    self.f.write('<thead>\n')
    self.f.write('<row>{0}\n'.format(self.tableHeaderColor))
    self.f.write('  <entry>Id</entry>\n')
    self.f.write('  <entry>Name</entry>\n')
    self.f.write('  <entry>Description</entry>\n')
    self.f.write('  <entry>Int Window (usec)</entry>\n')
    self.f.write('  <entry>Min Period (usec)</entry>\n')
    self.f.write('  <entry>Max Charge</entry>\n')
    self.f.write('</row>\n')

    self.f.write('</thead>\n')
    self.f.write('<tbody>\n')
    rowIndex = 0
    for powerClass in self.session.query(models.BeamClass).all():
      self.f.write('<row>{0}\n'.format(self.tableRowColor[rowIndex%2]))
      rowIndex=rowIndex+1
      self.f.write('  <entry>{0}</entry>\n'.format(powerClass.number))
      self.f.write('  <entry>{0}</entry>\n'.format(powerClass.name))
      self.f.write('  <entry>{0}</entry>\n'.format(powerClass.description))
      self.f.write('  <entry>{0}</entry>\n'.format(powerClass.integration_window))
      self.f.write('  <entry>{0}</entry>\n'.format(powerClass.min_period))
      self.f.write('  <entry>{0}</entry>\n'.format(powerClass.total_charge))
      self.f.write('</row>\n')

    self.f.write('</tbody>\n')
    self.f.write('</tgroup>\n')
    self.f.write('</table>\n')
    self.f.write('</section>\n')
 
  def writeDevices(self):
    self.f.write('<section><title>MPS Devices</title>\n')

    for device in self.session.query(models.Device).all():
      self.writeDeviceInfo(device)
    self.f.write('</section>\n')

  def writeLogicCondition(self, condition):
    self.f.write('<section><title>{0}: {1}</title>\n'.format(condition.name, condition.description))

    table_name = 'Condition Inputs'
    self.f.write('<table id="condition.{0}" xreflabel="{1}">\n'.format(condition.id, table_name))
    self.f.write('<title>{0}</title>\n'.format(table_name))
    self.f.write('<tgroup cols=\'3\' align=\'left\' colsep=\'2\' rowsep=\'2\'>\n')
    self.f.write('<colspec colname=\'c1\' colwidth="0.35*"/>')
    self.f.write('<colspec colname=\'c2\' colwidth="0.35*"/>')
    self.f.write('<colspec colname=\'c3\' colwidth="0.25*"/>')
    self.f.write('<thead>\n')
    self.f.write('<row>{0}\n'.format(self.tableHeaderColor))
    self.f.write('  <entry>Fault</entry>\n')
    self.f.write('  <entry>State</entry>\n')
    self.f.write('  <entry>Bit Position</entry>\n')
    self.f.write('</row>\n')
    
    self.f.write('</thead>\n')
    self.f.write('<tbody>\n')

    rowIndex = 0
    for input in condition.condition_inputs:
      faultState = self.session.query(models.FaultState).\
          filter(models.FaultState.id==input.fault_state_id).one()
      deviceState = self.session.query(models.DeviceState).filter(models.DeviceState.id==faultState.device_state_id).one()
      fault = self.session.query(models.Fault).filter(models.Fault.id==faultState.fault_id).one()
      self.f.write('<row>{0}\n'.format(self.tableRowColor[rowIndex%2]))
      rowIndex=rowIndex+1
      self.f.write('  <entry><link linkend=\'fault.{0}\'>{1}</link></entry>\n'.format(fault.id, fault.name))
      self.f.write('  <entry>{0}</entry>\n'.format(deviceState.name))
      self.f.write('  <entry>{0}</entry>\n'.format(input.bit_position))
      self.f.write('</row>\n')
        
    self.f.write('</tbody>\n')
    self.f.write('</tgroup>\n')
    self.f.write('</table>\n')

    self.f.write('<para>When the condition inputs in the above <link linkend=\'condition.{0}\'>table</link> are met, then the faults generated by the following devices are ignored (bypassed):</para>\n'.format(condition.id))

    table_name = 'Ignored Devices'
    self.f.write('<table>\n')
    self.f.write('<title>{0}</title>\n'.format(table_name))
    self.f.write('<tgroup cols=\'1\' align=\'left\' colsep=\'2\' rowsep=\'2\'>\n')
    self.f.write('<colspec colname=\'c1\' colwidth="0.9*"/>')

    self.f.write('<thead>\n')
    self.f.write('<row>{0}\n'.format(self.tableHeaderColor))
    self.f.write('  <entry>Device</entry>\n')
    self.f.write('</row>\n')
    
    self.f.write('</thead>\n')
    self.f.write('<tbody>\n')

    rowIndex = 0
    for ignoreCondition in condition.ignore_conditions:
      device = self.session.query(models.AnalogDevice).filter(models.AnalogDevice.id==ignoreCondition.analog_device_id).one()
      self.f.write('<row>{0}\n'.format(self.tableRowColor[rowIndex%2]))
      rowIndex=rowIndex+1
      self.f.write('  <entry><link linkend=\'device.{0}\'>{1}</link></entry>\n'.format(device.id, device.name))
      self.f.write('</row>\n')
        
    self.f.write('</tbody>\n')
    self.f.write('</tgroup>\n')
    self.f.write('</table>\n')
    self.f.write('</section>')



  def writeIgnoreLogic(self):
    self.f.write('<section><title>Ignore Logic</title>\n')

    for condition in self.session.query(models.Condition).all():
      self.writeLogicCondition(condition)

    self.f.write('</section>\n')

  def writeCrates(self):
    self.f.write('<section><title>ATCA Crates</title>\n')
    for crate in self.session.query(models.Crate).all():
      self.writeCrate(crate)
    self.f.write('</section>\n')      

  def exportHtml(self, fileName):
    cmd = 'xsltproc $PACKAGE_TOP/docbook-xsl/1.79.1/html/docbook.xsl {0} > {1}.html'.format(fileName, fileName.split(".")[0])
    os.system(cmd)

  def exportPdf(self, fileName):
    print fileName + " -> " + fileName.split(".")[0]
    cmd = 'xsltproc $PACKAGE_TOP/docbook-xsl/1.79.1/fo/docbook.xsl {0} > {1}.fo'.format(fileName, fileName.split(".")[0])
    os.system(cmd)

    cmd = 'fop -fo {0}.fo -rtf {0}.rtf'.format(fileName.split(".")[0])
    os.system(cmd)

    cmd = 'fop -fo {0}.fo -pdf {0}.pdf'.format(fileName.split(".")[0])
    os.system(cmd)

    cmd = '\rm {0}.fo'.format(fileName.split(".")[0])
    os.system(cmd)


  def exportDocBook(self, fileName):
    self.f = open(fileName, "w")

    self.writeHeader()

    self.writeMitigationDevices()

    self.writePowerClasses()

    self.writeCrates()

    self.writeAppCards()

    self.writeDevices()

    self.writeIgnoreLogic()

    self.f.write('</article>\n')
    self.f.close()

    self.exportHtml(fileName)
    self.exportPdf(fileName)

# --- Main ---

parser = argparse.ArgumentParser(description='Print database inputs/logic')
parser.add_argument('database', metavar='db', type=file, nargs=1,
                    help='database file name (e.g. mps_gun.db)')

args = parser.parse_args()

e = Exporter(args.database[0].name)
e.exportDocBook('{0}.xml'.format(args.database[0].name.split('.')[0]))

