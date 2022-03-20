#!/usr/bin/env python
from mps_database.mps_config import MPSConfig, models, runtime
from sqlalchemy import MetaData
from mps_database.tools.mps_names import MpsName
from mps_database.tools.mps_reader import MpsReader, MpsDbReader
import datetime
import argparse
import time
import yaml
import os
import sys
import json
import csv

class InputGeneration(MpsReader):

  def __init__(self,db_file,file_path,dest_path,clean,verbose):
    MpsReader.__init__(self,db_file=db_file,dest_path=dest_path,template_path=file_path,clean=clean,verbose=verbose)
    self.verbose = verbose
    self.filepath = file_path  
    self.export_devices = []

  def writeSubset(self,intypes,extypes,groups):
    for group in groups:
      if extypes == None:
        extypes = []
      filename = "{0}/Group{1}.csv".format(self.filepath,group)
      f = open(filename)
      line = f.readline().strip()
      fields=[]
      for field in line.split(','):
        fields.append(str(field).lower())
      while line:
        device_info={}
        line = f.readline().strip()
        if line:
          field_index = 0
          for property in line.split(','):
            device_info[fields[field_index]]=property
            field_index = field_index + 1
          if device_info['inconfig'].lower() != 'y':
            if device_info['type'] not in extypes:
              if intypes is not None:
                if device_info['type'] in intypes:
                  self.export_devices.append(device_info)
              else:
                self.export_devices.append(device_info)

      f.close()
      self.write_output_file()
  
  def write_output_file(self):
    filename = '{0}/out.csv'.format(self.dest_path)
    with open(filename,'w') as csvfile:
      fieldnames = ['ln','crate','slot','appid','channel','type','device','z','bit_position','z_name','o_name','auto_reset',
                    'evaluation','description','ignore','dest','slope','offset','cable','ln status','cn status','cn logic','checked date','inconfig']
      writer = csv.DictWriter(csvfile,fieldnames=fieldnames)
      writer.writeheader()
      for macro in self.export_devices:
        writer.writerow(macro)


parser = argparse.ArgumentParser(description='Create subset of devices based on type and location')
parser.add_argument('-v',action='store_true',default=False,dest='verbose',help='Verbose output')
parser.add_argument('--filepath',metavar='database',required=True,help='location of input CSV files')
parser.add_argument('--dest',metavar='destination',required=True,help='relative path to desired location of output csv')
parser.add_argument('--intypes',nargs='*',metavar='types',help='device types to add to concatenated file')
parser.add_argument('--extypes',nargs='*',metavar='types',help='device types to add to concatenated file')
parser.add_argument('--groups',nargs='*',type=int,metavar='groups',required=False,help='Groups to export as a list',default=[0,1,2,3,4,5,6,7,8,9,10,11])
parser.add_argument('-c',action='store_true',default=False,dest='clean',help='Clean export directories; default=False')
args = parser.parse_args()

clean=False
if args.clean:
  clean=True

verbose=False
if args.verbose:
  verbose=True

intypes = args.intypes
extypes = args.extypes

groups = args.groups


db_file=''
template_path = args.filepath
dest_path = args.dest

export_release = InputGeneration(db_file,template_path,dest_path,clean,verbose)
export_release.writeSubset(intypes,extypes,groups)
      
