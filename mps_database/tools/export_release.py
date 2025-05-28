#!/usr/bin/env python
from mps_database.mps_config import MPSConfig, models
from sqlalchemy import MetaData
from mps_database.tools.mps_db_reader import MpsDbReader
from mps_database.tools.mps_tools import MpsTools
from mps_database.tools.export_yaml import ExportYaml
from mps_database.tools.export_ln import ExportLinkNode
import argparse


parser = argparse.ArgumentParser(description='Export MPS configuration')
parser.add_argument('-v',action='store_true',default=False,dest='verbose',help='Verbose output')
parser.add_argument('-c',action='store_true',default=False,dest='clean',help='Clean export directories; default=False')
parser.add_argument('--db',metavar='database',required=True,help='MPS sqlite database file')
parser.add_argument('--ver',metavar='version',required=False,help='version number, if a new tag is desired')
parser.add_argument('-y',action='store_true',default=False,dest='yaml',help='Export YAML CN configuration files')
parser.add_argument('-l',action='store_true',default=False,dest='ln',help='Export application files')
args = parser.parse_args()

verbose=args.verbose
clean = args.clean
yaml = args.yaml
ln = args.ln
db_file = args.db
if args.ver:
  version = args.ver
else:
  version = '9999-99-99-z'

dest = '{0}/'.format(version)

tools = MpsTools(verbose)
tools.create_dir(dest,clean)

with MpsDbReader(db_file) as session:
  if yaml:
    export_yaml = ExportYaml(session,tools,dest,version,verbose)
    export_yaml.export()
  if ln:
    export_ln = ExportLinkNode(session,tools,dest,version,verbose)
    export_ln.export()