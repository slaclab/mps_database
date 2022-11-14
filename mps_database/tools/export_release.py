#!/usr/bin/env python
from mps_database.mps_config import MPSConfig, models, runtime
from sqlalchemy import MetaData
from mps_database.tools.mps_names import MpsName
from mps_database.tools.mps_reader import MpsReader, MpsDbReader
from mps_database.tools.export_link_node_groups import ExportLinkNodeGroups
from mps_database.tools.export_link_node import ExportLinkNode
from mps_database.tools.export_apps import ExportApplication
from mps_database.tools.export_device import ExportDevice
from mps_database.tools.export_faults import ExportFaults
from mps_database.tools.export_cn_extras import ExportCnExtras
from mps_database.tools.export_yaml import ExportYaml
from latex import Latex
import math
import argparse
import time
import yaml
import os
import sys
import shutil
    

parser = argparse.ArgumentParser(description='Export MPS configuration')
parser.add_argument('-v',action='store_true',default=False,dest='verbose',help='Verbose output')
parser.add_argument('--db',metavar='database',required=True,help='MPS sqlite database file')
parser.add_argument('--template',metavar='template',required=True,help='relative path to template files')
parser.add_argument('--dest',metavar='destination',required=True,help='relative path to desired location of output package')
parser.add_argument('-l',action='store_true',default=False,dest='link_node',help='Export Link Nodes Only, no CN')
parser.add_argument('-f',action='store_true',default=False,dest='fault',help='Export Faults Only, no LN')
parser.add_argument('-e',action='store_true',default=False,dest='extra',help='Export Extras')
parser.add_argument('-c',action='store_true',default=False,dest='clean',help='Clean export directories; default=False')
parser.add_argument('-r',action='store_true',default=False,dest='report',help='Do not generate reports, default True')
parser.add_argument('--ver',metavar='version',required=False,help='version number, if a new tag is desired')
args = parser.parse_args()
clean=False
if args.clean:
  clean=True

verbose=False
if args.verbose:
  verbose=True

link_node = False
if args.link_node:
  link_node = True

fault_arg = False
if args.fault:
  fault_arg = True

report = True
if args.report:
  report = False

extra = False
if args.extra:
  extra = True

db_file = args.db
template_path=args.template
dest_path=args.dest

ver = args.ver
if ver is not None:
  link_node = True
  fault_arg = True
  extra = True
  report = True
  clean = True
  print("INFO: New version {0} will be generated".format(ver))
  tagged_dbname = 'mps_config-{0}.db'.format(ver)
  shutil.copyfile(db_file, tagged_dbname)
  dest_path = ver
  db_file = tagged_dbname

with MpsDbReader(db_file) as session:
  export_group = ExportLinkNodeGroups(db_file,template_path,dest_path,clean,verbose,session)
  export_ln = ExportLinkNode(db_file,template_path,dest_path,False,verbose,session)
  export_app = ExportApplication(db_file,template_path,dest_path,False,verbose,session)
  export_device = ExportDevice(db_file,template_path,dest_path,False,verbose,session)
  export_fault = ExportFaults(db_file,template_path,dest_path,False,verbose,session)
  export_extra = ExportCnExtras(db_file,template_path,dest_path,False,verbose,session)
  export_yaml = ExportYaml(db_file,template_path,dest_path,False,verbose,session)
  if link_node:
    crate_profiles = export_group.startReport('crate','Appendix A: SCMPS Crate Profiles')
    input_report = export_group.startReport('input','Appendix B: SCMPS Input Display')
    groups = session.query(models.LinkNodeGroup).order_by(models.LinkNodeGroup.number).all()
    global_macros = []
    for group in groups:
      export_group.generate_group_alarm(group)
      crate_profiles.startGroup(group.number)
      if group.has_inputs():
        input_report.startGroup(group.number)
      lns = group.link_nodes
      export_group.generate_group_display(group.number,lns)
      for ln in lns:
        rows = []
        disp_macros = []
        export_ln.export_epics(ln)
        crate_profiles.startLinkNode(ln.lcls1_id,ln.crate.location)
        export_ln.writeCrateProfile(ln,crate_profiles)
        export_ln.generate_crate_display(ln)
        apps = session.query(models.ApplicationCard).filter(models.ApplicationCard.link_node==ln).order_by(models.ApplicationCard.slot_number).all()
        for a in apps:
          export_app.export_epics(a)
          export_app.export_displays(a)
          export_app.export_cn_app_id(a)
          export_app.write_cn_status_macros(a,global_macros)
          if len(a.analog_channels) > 0:
            export_device.export_analog(a,rows,disp_macros)
          if len(a.digital_channels) > 0:
            export_device.export_digital(a,rows,disp_macros)
            export_device.write_ln_input_display(a)
        if len(rows) > 0:
          input_report.startLinkNode(ln.lcls1_id,ln.crate.location)
          input_report.writeAppInputs(rows)
        export_ln.export_cn_input_display(ln,disp_macros)
    export_app.write_cn_status_macro_file(global_macros)
    if report:
      export_group.endReport(crate_profiles)
      export_group.endReport(input_report)
  if fault_arg:
    ignore_groups = []
    report_faults = []
    logic_report = export_fault.startReport('Appendix C: SCMPS Logic Checkout')
    faults = session.query(models.Fault).order_by(models.Fault.description).all()
    for fault in faults:
      export_fault.export_fault_epics(fault)
      export_fault.link_fault_to_ignore_group(fault,ignore_groups,report_faults)
    if verbose:
      print("INFO: Export Fault Report...")
    export_fault.writeLogicTables(report_faults,ignore_groups,logic_report)
    if verbose:
      print("INFO: Done exporting Fault Report...")
    if report:
      export_fault.endReport(logic_report)
  if extra:
    export_extra.export_conditions()
    export_extra.export_destinations()
    export_extra.generate_area_displays()
    export_yaml.export()

kludge_dest = "{0}/link_node_db/app_db/cpu-bsys-sp02/0001/03".format(dest_path)
kludge_source = "{0}/link_node_db/app_db/cpu-bsys-sp02/0101/02".format(dest_path)
shutil.move(kludge_source,kludge_dest)
shutil.rmtree("{0}/link_node_db/app_db/cpu-bsys-sp02/0101/".format(dest_path))

if ver is not None:
  destination = "{0}/{1}".format(dest_path,tagged_dbname)
  shutil.move(tagged_dbname,destination)
    

    
