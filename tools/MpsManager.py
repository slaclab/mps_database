#!/usr/bin/env python

import socket
import sys
import os
import errno
import argparse
import time
import datetime

from mps_config import MPSConfig, models
from threshold_restorer import ThresholdRestorer

from ctypes import *
    
#
# Messages:
# 
# type = 100 => Threshold restore request
#   id => Application ID (global ID)
#
class Message(Structure):
    _fields_ = [
        ("type", c_uint),
        ("id", c_uint),
        ("oldValue", c_uint),
        ("newValue", c_uint),
        ("aux", c_uint),
        ]

class MpsManager:
  session = 0
  host = 'lcls-dev3'
  port = 4478
  logFileName = '/tmp/mpshist'
  fileSize = 1024*1024*10
  sock = 0
  stdout = False
  logFile = None
  logFileName = None
  messageCount = 0
  fileSizeCheckCount = 5
  currentFileName = None

  def __init__(self, host, port, logFileName, fileSize, stdout, dbFileName, verbose):
      self.mps = MPSConfig(args.database[0].name, args.database[0].name.split('.')[0]+'_runtime.db')
      self.session = self.mps.session
      self.host = host
      self.port = port
      self.logFileName = logFileName
      self.fileSize = fileSize
      self.stdout = stdout
      self.file = None
      self.verbose = verbose
      self.restorer = ThresholdRestorer(mps=self.mps, verbose=self.verbose)

      # create dgram udp socket
      try:
          self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      except socket.error:
          print 'Failed to create socket'
          sys.exit()

      print('Listening on port {}'.format(port))

      if (self.logFileName != None):
          if (self.open_new_log_file() == False):
              exit(1)

      myAddr = (self.host, self.port)
      self.sock.bind(myAddr)
  
  def __del__(self):
    self.session.close()

  def show_info(self):
      if self.stdout:
          print '+ Messages to console'

      if self.logFileName != None:
          print '+ Messages to file (basename={0})'.format(self.logFileName)
          if (self.fileSize < 1024):
              sizeStr = str(self.fileSize) + ' bytes'
          elif (self.fileSize < 1024 * 1024):
              sizeStr = str(self.fileSize/1024) + ' Kbytes'
          elif (self.fileSize < 1024 * 1024 * 1024):
              sizeStr = str(self.fileSize/(1024*1014)) + ' Mbytes'
          else:
              sizeStr = str(self.fileSize/(1024*1014*1024)) + ' Gbytes'
          print '+ Maximum log file size={0}'.format(sizeStr)

  def run(self):
      done = False
      print "=== MpsManager  ==="
#      self.show_info()
      while not done:
          self.receive_request()

  def open_new_log_file(self):
      if (self.file != None):
          print '= Closing file {0} (size={1} bytes)'.format(self.currentFileName, self.file.tell())
          self.file.close()

      self.currentFileName = '{0}-{1}.log'.format(logFileName, datetime.datetime.now().strftime('%Y.%m.%d-%H:%M:%S'))
      try:
          print '= Opening new log file {0}'.format(self.currentFileName)
          self.file = open(self.currentFileName, 'w')
      except IOError as e:
          if e.errno == errno.EACCES:
              print 'ERROR: No permission to write file {0}'.format(self.currentFileName)
          else:
              print 'ERROR: errno={0}, cannot write to file {1}'.format(e.errno, self.currentFileName)
          return False
      return True

  def restore_thresholds(self, app_id):
      print("Restore thresholds for {}".format(app_id))
      if (not self.restorer.restore(app_id, release=True)):
          print("Failed to restore")

  def process_request(self, message):
    if (message.type == 100): # FaultStateType
        self.restore_thresholds(message.id)
    else:
        self.printGeneric("?????", message)

  def receive_request(self):
    message=Message(0, 0, 0, 0, 0)
    data, ipAddr = self.sock.recvfrom(sizeof(Message))
    if data:
        message = Message.from_buffer_copy(data)
        self.process_request(message)

parser = argparse.ArgumentParser(description='Receive MPS status messages')
parser.add_argument('--port', metavar='port', type=int, nargs='?', help='server port (default=4478)')
parser.add_argument('database', metavar='db', type=file, nargs=1,
                    help='database file name (e.g. mps_gun_config.db)')
parser.add_argument('--log-file', metavar='file', type=str, nargs='?',
                    help='Manager log file, e.g. /data/mpsmanager - file will be /data/mpsmanager-<DATE>.log')
parser.add_argument('--file-size', metavar='file_size', type=int, nargs='?', 
                    help='Maximum log file size (default=100 MB)')
parser.add_argument('-c', action='store_true', default=False, dest='stdout', help='Print messages to stdout')
parser.add_argument('-v', action='store_true', default=False,
                    dest='verbose', help='verbose output')
args = parser.parse_args()


#if args.host:
#    host = args.host[0]
#else:    
#    host = 'lcls-dev3'
host = socket.gethostname()

fileSize=1024*1024*100
if args.file_size:
    fileSize = args.file_size

logFileName=None
if args.log_file:
    logFileName = args.log_file

stdout=False
if args.stdout:
    stdout=True

port=4478
if args.port:
    port = args.port

manager = MpsManager(host, port, logFileName, fileSize, stdout, args.database[0].name, args.verbose)
manager.run()

