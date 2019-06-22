#!/usr/bin/env python
#
# Script for restoring thresholds for MPS analog devices. Thresholds for analog devices
# for the specified global app id will be restored using values in the runtime database
#
# Exit codes:
# 1 - Failed to restore one or more PVs
# 2 - Failed to check on or more PVs
#

from mps_config import MPSConfig, models, runtime
from mps_names import MpsName
from runtime_utils import RuntimeChecker
from runtime import *
from sqlalchemy import func
import sys
import argparse
import time 
import os
import re
import subprocess
import yaml
import epics
from epics import PV
from argparse import RawTextHelpFormatter
from threshold_restorer import ThresholdRestorer

#=== MAIN ==================================================================================

parser = argparse.ArgumentParser(description='Restore threshold values from the runtime database',
                                 formatter_class=RawTextHelpFormatter)
parser.add_argument('database', metavar='db', type=file, nargs=1, 
                    help='database file name (e.g. mps_gun.db, where the runtime database is named mps_gun_runtime.db')

parser.add_argument('--app-id', metavar='ID', type=int, nargs='?', help='application global id')
parser.add_argument('-c', action='store_true', default=False, dest='check',
                    help='read back threshold values from PV and compare with runtime database thresholds')
parser.add_argument('-f', action='store_true', default=False, dest='force_write',
                    help='restore thresholds even if PVs are not writable (changes only the database)')
parser.add_argument('-v', action='store_true', default=False,
                    dest='verbose', help='verbose output')

proc = subprocess.Popen('whoami', stdout=subprocess.PIPE)
user = proc.stdout.readline().rstrip()

args = parser.parse_args()

tr = ThresholdRestorer(args.database[0].name,
                       args.database[0].name.split('.')[0]+'_runtime.db',
                       args.force_write, args.verbose)
if (not tr.restore(args.app_id)):
  exit(1)

if (args.check):
  if (not tr.check(args.app_id)):
    exit(2)

