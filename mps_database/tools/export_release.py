#!/usr/bin/env python
from mps_database.mps_config import MPSConfig, models, runtime
from sqlalchemy import MetaData
from mps_database.tools.mps_names import MpsName
from mps_database.tools.mps_reader import MpsReader, MpsDbReader
from mps_database.tools.export_faults import ExportFaults
from mps_database.tools.export_link_node_groups import ExportLinkNodeGroups
from mps_database.tools.export_yaml import ExportYaml
from mps_database.tools.export_cn_extras import ExportCnExtras
from latex import Latex
import math
import argparse
import time
import yaml
import os
import sys
import shutil

class ExportRelease(MpsReader):

  def __init__(self, db_file, template_path, dest_path,clean, verbose,devices,yaml,faults,report=True):
    MpsReader.__init__(self,db_file=db_file,dest_path=dest_path,template_path=template_path,clean=clean,verbose=verbose)
    self.export_lns = ExportLinkNodeGroups(db_file,template_path,dest_path,False,verbose,report)
    self.export_faults = ExportFaults(db_file,template_path,dest_path,False,verbose,report)
    self.export_yaml = ExportYaml(db_file,template_path,dest_path,False,verbose)
    self.export_extra = ExportCnExtras(db_file,template_path,dest_path,False,verbose)
    self.report = report
    self.verbose = verbose
    self.yaml = yaml
    self.devices = devices
    self.faults = faults

  def export(self):
    if self.verbose:
      print("INFO: Beginning Export Process")
    with MpsDbReader(db_file) as mps_db_session:
      if self.devices:
        self.export_lns.export(mps_db_session)
      if self.faults:
        self.export_faults.export(mps_db_session)
        self.export_extra.export_conditions(mps_db_session)
        self.export_extra.export_destinations(mps_db_session)
      if self.yaml:
        self.export_yaml.export(mps_db_session)
        self.export_extra.generate_area_displays(mps_db_session)
    if self.verbose:
      print("INFO: Done Export Process")
    

parser = argparse.ArgumentParser(description='Create MPS database')
parser.add_argument('-v',action='store_true',default=False,dest='verbose',help='Verbose output')
parser.add_argument('--db',metavar='database',required=True,help='MPS sqlite database file')
parser.add_argument('--template',metavar='template',required=True,help='relative path to template files')
parser.add_argument('--dest',metavar='destination',required=True,help='relative path to desired location of output package')
parser.add_argument('--ver',metavar='version',required=False,help='version number, if a new tag is desired')
parser.add_argument('-c',action='store_true',default=False,dest='clean',help='Clean export directories; default=False')
parser.add_argument('-r',action='store_true',default=False,dest='report',help='Do not generate reports, default True')
parser.add_argument('-d',action='store_true',default=False,dest='devices',help='Should Generate device output')
parser.add_argument('-f',action='store_true',default=False,dest='faults',help='Should Generate fault output')
parser.add_argument('-y',action='store_true',default=False,dest='yaml',help='Should Generate yaml output')
args = parser.parse_args()

clean=False
if args.clean:
  clean=True

verbose=False
if args.verbose:
  verbose=True

devices=False
if args.devices:
  devices=True

faults=False
if args.faults:
  faults=True

yaml=False
if args.yaml:
  yaml=True

if not devices and not faults and not yaml:
  devices = True
  faults = True
  yaml = True

report = True
if args.report:
  report = False

db_file=args.db
template_path = args.template
dest_path = args.dest

ver = args.ver
if ver is not None:
  # Tag a new version - ignore dest input
  print("INFO: New version {0} will be generated".format(ver))
  tagged_dbname = 'mps_config-{0}.db'.format(ver)
  shutil.copyfile(db_file, tagged_dbname)
  dest_path = ver
  db_file = tagged_dbname
  report = True
  clean = True
  devices = True
  faults = True
  yaml = True

export_release = ExportRelease(db_file,template_path,dest_path,clean,verbose,devices,yaml,faults,report)
export_release.export()

if ver is not None:
  destination = "{0}/{1}".format(dest_path,tagged_dbname)
  shutil.move(tagged_dbname,destination)
