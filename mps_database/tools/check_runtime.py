#!/usr/bin/env python

from mps_database.mps_config import MPSConfig, models, runtime
from .runtime_utils import RuntimeChecker
from sqlalchemy import func
import sys
import argparse
import time 
import os

#=== MAIN ==================================================================================

parser = argparse.ArgumentParser(description='Check consistency between MPS configuration and runtime databases')
parser.add_argument('database', metavar='db', type=file, nargs=1, 
                    help='database file name (e.g. mps_gun.db)')
parser.add_argument('rt_database', metavar='runtime_db', type=file, nargs=1, 
                    help='runtime database file name (e.g. mps_gun_runtime.db)')
parser.add_argument('-v', action='store_true', default=False,
                    dest='verbose', help='Verbose output')

args = parser.parse_args()

mps = MPSConfig(args.database[0].name, args.rt_database[0].name)
session = mps.session
rt_session = mps.runtime_session

rc = RuntimeChecker(session, rt_session, args.verbose)
if (rc.check_databases()):
  print('Passed database runtime check.')

session.close()
rt_session.close()
