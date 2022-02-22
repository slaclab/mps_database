#!/usr/bin/env python
from mps_database.mps_config import MPSConfig, models
from mps_database.tools.mps_names import MpsName
from mps_database.tools.mps_reader import MpsReader, MpsDbReader
from sqlalchemy import func, exc, Column
import argparse
import time
import os
import subprocess
import errno
import re
import shutil
import datetime
import ipaddress
import json

class ExportCsv(MpsReader):

  def __init__(self, db_file, template_path, dest_path,clean, verbose):
    MpsReader.__init__(self,db_file=db_file,dest_path=dest_path,template_path=template_path,clean=clean,verbose=verbose)
    self.verbose = verbose
    self.groups = [0]

  def export(self):
    if self.verbose:
      print("INFO: Beginning Export Process")
    with MpsDbReader(db_file) as mps_db_session:
      for group in self.groups:
        link_nodes = mps_db_session.query(models.LinkNode).filter(models.LinkNode.group == group).order_by(models.LinkNode.lcls1_id).all()
        for ln in link_nodes:
          print(ln.lcls1_id)
      



parser = argparse.ArgumentParser(description='Create MPS database')
parser.add_argument('-v',action='store_true',default=False,dest='verbose',help='Verbose output')
parser.add_argument('--db',metavar='database',required=True,help='MPS sqlite database file')
parser.add_argument('--dest',metavar='destination',required=True,help='relative path to desired location of output package')
parser.add_argument('--template',metavar='template',required=True,help='relative path to template files')
parser.add_argument('-c',action='store_true',default=False,dest='clean',help='Clean export directories; default=False')
args = parser.parse_args()

verbose=False
if args.verbose:
  verbose=True

clean=False
if args.clean:
  clean=True

db_file=args.db
template_path = args.template
dest_path = args.dest

export = ExportCsv(db_file,template_path,dest_path,clean,verbose)
export.export()
