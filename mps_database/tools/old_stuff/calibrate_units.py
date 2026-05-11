#!/usr/bin/env python
from mps_database.mps_config import MPSConfig, models, runtime
from sqlalchemy import MetaData
from mps_database.tools.mps_names import MpsName
from mps_database.tools.mps_reader import MpsReader, MpsDbReader
from epics import caget, caput
import math
import argparse
import time
import yaml
from os import path
from glob import glob
import sys
import shutil

class Calibrate(MpsReader):

  def __init__(self, db_file, verbose,session,slope,cont,so):
    MpsReader.__init__(self,db_file=db_file,dest_path='',template_path='',clean=False,verbose=verbose)
    self.mps_names = MpsName(session)
    self.slope = slope
    self.cont = cont
    self.verbose = verbose
    self.slope_only = so

  def get_device(self,session,device):
    dt = None
    d = None
    if device == 'PBLM':
      dt = 'PBLM'
    elif device == 'LBLM':
      dt = 'LBLM'
    elif device == 'CBLM':
      dt = 'CBLM'
    elif device == 'SBLM':
      dt = 'SBLM'
    if dt is not None:
      dtype = session.query(models.DeviceType).filter(models.DeviceType.name == 'BLM').one()
      d = session.query(models.AnalogDevice).filter(models.AnalogDevice.name.contains(dt)).filter(models.AnalogDevice.device_type==dtype).all()
    else:
      d = session.query(models.AnalogDevice).filter(models.AnalogDevice.name.contains(device)).all()
    return d

  def get_pv_prefix(self,session,devices):
    pvs = []
    for d in devices:
      name = self.mps_names.getDeviceName(d)
      fis = session.query(models.FaultInput).filter(models.FaultInput.device == d).all()
      faults = []
      for fi in fis:
        fault = fi.fault
        faults.append(fault)
      for f in faults:
        pv_name = '{0}:{1}'.format(name,f.name)
        pvs.append(pv_name)
    return pvs

  def reset_calibration(self,dev):
    pv = '{0}_SLOPE'.format(dev)
    caput(pv,1)
    pv = '{0}_OFFSET'.format(dev)
    caput(pv,0)
    time.sleep(0.5)

  def calibrate(self,pvs):
    for pv in pvs:
      if self.verbose:
        print('Working on Device: {0}'.format(pv))
      self.reset_calibration(pv)
      if self.cont:
        average = self.get_average_value(pv)
        if self.verbose:
          print("    Slope = {0} EGU/raw, Offset = {1} raw".format(slope,average))
        if self.slope_only:
          if self.verbose:
            print('    Slope Only! Offset = 0')
          average = 0
        ipv = '{0}_SLOPE'.format(pv)
        caput(ipv,self.slope)
        ipv = '{0}_OFFSET'.format(pv)
        caput(ipv,average)    

  def get_average_value(self,pv):
    sum = 0
    num = 50
    count = 0
    for i in range(0,num):
      count+=1
      sum += caget(pv)
      time.sleep(.1)
    average = sum/count
    return average
      

parser = argparse.ArgumentParser(description='Unit calibration')
parser.add_argument('-v',action='store_true',default=False,dest='verbose',help='Verbose output')
parser.add_argument('-r',action='store_true',default=False,dest='reset',help='Use flag to reset slope to 1 and offset to 0.  Omit flag to set new slope and offset')
parser.add_argument('--slope',metavar='slope',required=False,default=0.039673,help='Slope in EGU/raw, default = 0.039673 mV/raw')
parser.add_argument('--db',metavar='database',required=False,help='MPS sqlite database file')
parser.add_argument('--dev',metavar='device',required=True,help='Device to calibrate. Can use PBLM,LBLM,or CBLM for batch.  Can send in list of devices')
args = parser.parse_args()
verbose = False
if args.verbose:
  verbose = True

cont = True
if args.reset:
  cont = False

dev = args.dev
slope=float(args.slope)

slope_only = False
if 'CBLM' in dev:
  slope_only = True

phys_top = path.expandvars('$PHYSICS_TOP')
phys_top += "/mps_configuration/current/"
db_file = glob(phys_top + "mps_config*.db")[0]

if args.db:
  db_file = args.db

with MpsDbReader(db_file) as session:
  calibrate = Calibrate(db_file,verbose,session,slope,cont,slope_only)
  devices = calibrate.get_device(session,dev)
  pvs = calibrate.get_pv_prefix(session,devices)
  calibrate.calibrate(pvs)
