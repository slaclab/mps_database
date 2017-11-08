#!/usr/bin/env python

import socket
import sys
import os
import errno
import argparse
import time
import datetime

from mps_config import MPSConfig, models

from ctypes import *
    
class Message(Structure):
    _fields_ = [
        ("type", c_uint),
        ("id", c_uint),
        ("oldValue", c_uint),
        ("newValue", c_uint),
        ("aux", c_uint),
        ]

class HistoryLogger: 
  session = 0
  host = 'lcls-dev3'
  port = 3356
  fileName = '/tmp/mpshist'
  fileSize = 1024*1024*10
  sock = 0
  stdout = False
  logFile = None
  logFileName = None
  messageCount = 0
  fileSizeCheckCount = 5
  currentFileName = None

  def __init__(self, host, port, fileName, fileSize, stdout, dbFileName):
      mps = MPSConfig(args.database[0].name)
      self.session = mps.session
      self.host = host
      self.port = port
      self.fileName = fileName
      self.fileSize = fileSize
      self.stdout = stdout
      self.file = None

      # create dgram udp socket
      try:
          self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      except socket.error:
          print 'Failed to create socket'
          sys.exit()

      if (self.fileName != None):
          if (self.openNewLogFile() == False):
              exit(1)

#      currentFileName = '{0}-{1}.hist'.format(fileName, datetime.datetime.now().strftime('%Y.%m.%d-%H:%M:%S'))
#      try:
#          self.file = open(currentFileName, 'w')
#      except IOError as e:
#          if e.errno == errno.EACCES:
#              print 'ERROR: No permission to write file {0}'.format(currentFileName)
#          else:
#              print 'ERROR: errno={0}, cannot write to file {1}'.format(e.errno, currentFileName)
#          exit(-1)
 
      myAddr = (self.host, self.port)
      self.sock.bind(myAddr)
  
  def __del__(self):
    self.session.close()

  def showInfo(self):
      if self.stdout:
          print '+ Messages to console'

      if self.fileName != None:
          print '+ Messages to file (basename={0})'.format(self.fileName)
          if (self.fileSize < 1024):
              sizeStr = str(self.fileSize) + ' bytes'
          elif (self.fileSize < 1024 * 1024):
              sizeStr = str(self.fileSize/1024) + ' Kbytes'
          elif (self.fileSize < 1024 * 1024 * 1024):
              sizeStr = str(self.fileSize/(1024*1014)) + ' Mbytes'
          else:
              sizeStr = str(self.fileSize/(1024*1014*1024)) + ' Gbytes'
          print '+ Maximum log file size={0}'.format(sizeStr)

  def log(self):
      done = False
      print "=== History Server ==="
      self.showInfo()
      while not done:
          self.receiveUpdate()

  def openNewLogFile(self):
      if (self.file != None):
          print '= Closing file {0} (size={1} bytes)'.format(self.currentFileName, self.file.tell())
          self.file.close()

      self.currentFileName = '{0}-{1}.hist'.format(fileName, datetime.datetime.now().strftime('%Y.%m.%d-%H:%M:%S'))
      try:
          print '= Opening new history file {0}'.format(self.currentFileName)
          self.file = open(self.currentFileName, 'w')
      except IOError as e:
          if e.errno == errno.EACCES:
              print 'ERROR: No permission to write file {0}'.format(self.currentFileName)
          else:
              print 'ERROR: errno={0}, cannot write to file {1}'.format(e.errno, self.currentFileName)
          return False
      return True

  def logString(self, messageString):
      if stdout:
          print messageString

      if self.fileName != None:
          self.file.write(messageString + '\n')

          self.messageCount = self.messageCount + 1
          if (self.messageCount == self.fileSizeCheckCount):
              print 'Size={0}'.format(self.file.tell())
              if (self.file.tell() > self.fileSize):
                  self.openNewLogFile()
              self.messageCount = 0

  def printGeneric(self, messageType, message):
      messageString = 'type={0}, id={1}, old={2}, new={3}, aux={4}'.\
          format(message.type, message.id, message.oldValue, message.newValue, message.aux)
      self.logString('[{0}][{1}] {2}'.format(time.asctime(time.localtime(time.time())),
                                             messageType, messageString))

  def printMessage(self, messageType, messageString):
      self.logString('[{0}][{1}] {2}'.format(time.asctime(time.localtime(time.time())),
                                             messageType, messageString))

  def printMitigation(self, message):
    try:
        device = self.session.query(models.MitigationDevice).filter(models.MitigationDevice.id==message.id).first()
        bc1 = self.session.query(models.BeamClass).filter(models.BeamClass.id==message.oldValue).first()
        bc2 = self.session.query(models.BeamClass).filter(models.BeamClass.id==message.newValue).first()

        self.printMessage('MITGN', '{0}: {1} -> {2}'.format(device.name, bc1.name, bc2.name))
    except:
        self.printGeneric('MITGN', message)

  def printFault(self, message):
    messageType = "FAULT"
    try:
        fault = self.session.query(models.Fault).filter(models.Fault.id==message.id).first()
        if message.aux > 0:
            deviceState = self.session.query(models.DeviceState).filter(models.DeviceState.id==message.aux).first()

        newState = "OK"
        if message.newValue == 1:
            newState = "FAULTED"
            
        if message.aux > 0:
            messageString = '{0}: -> {1} ({2})'.format(fault.description, newState, deviceState.name)
        else:
            messageString = '{0}: -> {1}'.format(fault.description, newState)
 
        self.printMessage(messageType, messageString)

    except:
        self.printGeneric(messageType, message)

  def printBypassState(self, message):
    messageType = "BYPAS"
    try:
        if (message.aux > 31) :
            deviceInput = self.session.query(models.DeviceInput).filter(models.DeviceInput.id==message.id).first()
            channel = self.session.query(models.DigitalChannel).filter(models.DigitalChannel.id==deviceInput.channel_id).first()
        else:
            analogDevice = self.session.query(models.AnalogDevice).filter(models.AnalogDevice.id==message.id).first()
            channel = self.session.query(models.AnalogChannel).filter(models.AnalogChannel.id==analogDevice.channel_id).first()

        if (message.oldValue == 0):
            oldName = "Valid"
        else:
            oldName = "Expired"

        if (message.newValue == 0):
            newName = "Valid"
        else:
            newName = "Expired"

        if (message.aux > 31) :
            messageString = '{0}: {1} -> {2}'.format(channel.name, oldName, newName)
        else:
            messageString = '{0}: {1} -> {2} (integrator {3})'.format(channel.name, oldName, newName, message.aux)

        self.printMessage(messageType, messageString)
    except:
        self.printGeneric(messageType, message)

  def printDeviceInput(self, message):
    messageType = "INPUT"
    try:
        deviceInput = self.session.query(models.DeviceInput).filter(models.DeviceInput.id==message.id).first()
        channel = self.session.query(models.DigitalChannel).filter(models.DigitalChannel.id==deviceInput.channel_id).first()

        oldName = channel.z_name
        newName = channel.z_name
        if (message.oldValue > 0):
            oldName = channel.o_name
        if (message.newValue > 0):
            newName = channel.o_name

        messageString = '{0}: {1} -> {2}'.format(channel.name, oldName, newName)
        self.printMessage(messageType, messageString)

    except:
        self.printGeneric(messageType, message)

  def printAnalogDevice(self, message):
    messageType = "INPUT"
    try:
        analogDevice = self.session.query(models.AnalogDevice).filter(models.AnalogDevice.id==message.id).first()
        channel = self.session.query(models.AnalogChannel).filter(models.AnalogChannel.id==analogDevice.channel_id).first()

        messageString = '{0}: {1} -> {2}'.format(channel.name, hex(message.oldValue), hex(message.newValue))
        self.printMessage(messageType, messageString)

    except:
        self.printGeneric(messageType, message)


  def decodeMessage(self, message):
    if (message.type == 1): # FaultStateType
        self.printFault(message)
    elif (message.type == 2): # BypassStateType
        self.printBypassState(message)
    elif (message.type == 4): # MitigationType
        self.printMitigation(message)
    elif (message.type == 5): # DeviceInput (DigitalChannel)
        self.printDeviceInput(message)
    elif (message.type == 6): # AnalogDevice
        self.printAnalogDevice(message)
    else:
        self.printGeneric("?????", message)

  def receiveUpdate(self):
    message=Message(0, 0, 0, 0, 0)
    data, ipAddr = self.sock.recvfrom(sizeof(Message))
    if data:
        message = Message.from_buffer_copy(data)
        self.decodeMessage(message)

parser = argparse.ArgumentParser(description='Receive MPS status messages')
parser.add_argument('--host', metavar='hostname', type=str, nargs=1, help='Central node hostname')
parser.add_argument('--port', metavar='port', type=int, nargs='?', help='server port (default=3356)')
parser.add_argument('database', metavar='db', type=file, nargs=1,
                    help='database file name (e.g. mps_gun_config.db)')
parser.add_argument('--file', metavar='file', type=str, nargs='?',
                    help='History log file base, e.g. /data/history/mpshist - file will be /data/history/mpshist-<DATE>.txt')
parser.add_argument('--file-size', metavar='file_size', type=int, nargs='?', 
                    help='Maximum history log file size (default=10 MB)')
parser.add_argument('-c', action='store_true', default=False, dest='stdout', help='Print messages to stdout')
args = parser.parse_args()


if args.host:
    host = args.host[0]
else:    
    host = 'lcls-dev3'

fileSize=1024*1024*10
if args.file_size:
    fileSize = args.file_size

fileName=None
if args.file:
    fileName = args.file

stdout=False
if args.stdout:
    stdout=True

port=3356
if args.port:
    port = args.port

hist = HistoryLogger(host, port, fileName, fileSize, stdout, args.database[0].name)
hist.log()

