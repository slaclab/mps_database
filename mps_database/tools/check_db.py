#!/usr/bin/env python
from mps_database.mps_config import MPSConfig, models
from sqlalchemy import MetaData
from mps_database.tools.mps_db_reader import MpsDbReader
import argparse


parser = argparse.ArgumentParser(description='Export MPS configuration')
parser.add_argument('--db',metavar='database',required=True,help='MPS sqlite database file')
args = parser.parse_args()

db_file = args.db

with MpsDbReader(db_file) as session:
  for ch in session.query(models.AnalogChannel).all():
    if ch.wf_only:
      print(ch.name)