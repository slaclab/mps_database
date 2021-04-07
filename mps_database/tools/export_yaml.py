#!/usr/bin/env python

from Cheetah.Template import Template

from sqlalchemy import func
import sys
import os
import subprocess
import time
import argparse
from mps_database import ioc_tools
from mps_database.mps_config import MPSConfig, models

#=== MAIN ==================================================================================

parser = argparse.ArgumentParser(description='Export MPS sqlite database to YAML')

parser.add_argument('database', metavar='database', type=file, nargs=1, 
                    help='MPS database file name (e.g. mps_gun.db)')

parser.add_argument('yaml', metavar='yaml', type=str, nargs=1, 
                    help='exported YAML database file name (e.g. mps_gun.yaml)')

args = parser.parse_args()

mps=MPSConfig(args.database[0].name)
ioc_tools.dump_db_to_yaml(mps, args.yaml[0])

#
# Write header info to YAML file, so it is possible to identify when it was generated
#
#
# ---
# DatabaseInfo:
# - source: "/path/mps_gun_config.db"
#   date: "Wed Oct 18 14:33:59 PDT 2017"
#   user: "lpiccoli"
#   md5sum: "d9604d932498e7f6c2b77afbcd0a2fa7"
#
timestr = time.strftime("%Y%m%d-%H%M%S")
db_info_file_name = '{0}-{1}.yaml'.format('/tmp/header', timestr)
db_info_file = open(db_info_file_name, "w")

cmd = "whoami"
process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
user_name, error = process.communicate()

cmd = "md5sum {0}".format(args.database[0].name)
process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
md5sum_output, error = process.communicate()

md5sum_tokens = md5sum_output.split()

db_info_file.write("---\n")
db_info_file.write("DatabaseInfo:\n")
db_info_file.write("- source: {0}\n".format(args.database[0].name))
db_info_file.write("  date: {0}\n".format(time.asctime(time.localtime(time.time()))))
db_info_file.write("  user: {0}\n".format(user_name.strip()))
db_info_file.write("  md5sum: {0}\n".format(md5sum_tokens[0].strip()))
db_info_file.close()

cmd = "cat {0} >> {1}".format(db_info_file_name, args.yaml[0])
os.system(cmd)
