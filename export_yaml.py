#!/usr/bin/env python

from Cheetah.Template import Template

from sqlalchemy import func
import sys
import argparse
import ioc_tools
from mps_config import MPSConfig, models

#=== MAIN ==================================================================================

parser = argparse.ArgumentParser(description='Export EPICS template database')

parser.add_argument('database', metavar='database', type=file, nargs=1, 
                    help='MPS database file name (e.g. mps_gun.db)')

parser.add_argument('yaml', metavar='yaml', type=str, nargs=1, 
                    help='exported YAML database file name (e.g. mps_gun.yaml)')

args = parser.parse_args()

mps=MPSConfig(args.database[0].name)
ioc_tools.dump_db_to_yaml(mps, args.yaml[0])
print 'Done.'
