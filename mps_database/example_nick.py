#!/usr/bin/env python
from mps_database.mps_config import MPSConfig, models
from sqlalchemy import MetaData
from mps_database import tools
import argparse
from sqlalchemy import Column, Integer, Float, String, Boolean

parser = argparse.ArgumentParser(description="Example to extract crate profile")
parser.add_argument('--db',metavar='database',required=True,help='MPS sqlite database')
parser.add_argument('--ln',metavar='link_node',required=True,help='Link Node Number')
args = parser.parse_args()

db = args.db
lnid = args.ln

mps_config = MPSConfig(args.db)

session = mps_config.get_session()

ln = session.query(models.LinkNode).filter(models.LinkNode.lnid==lnid).one()
print("----------------------------")
print("Link Node: {0}".format(lnid))
print("Crate: {0}".format(ln.crate.get_full_location()))
print("CPU: {0}".format(ln.crate.get_cpu_nodename()))
print("SHM: {0}".format(ln.crate.get_nodename()))
print("Slot\tApp ID\tType")
print("----------------------------")
for c in ln.crate.cards:
  print("{0}\t{1}\t{2}".format(c.slot,c.number,c.type.name))
print("----------------------------")