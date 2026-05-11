#!/usr/bin/env python
from mps_database.mps_config import MPSConfig, models
from sqlalchemy import MetaData
import yaml
from yaml import MappingNode, ScalarNode
from sqlalchemy import Column, Integer, Float, String, Boolean
import os

class ExportReport():

  def __init__(self,session,tools,st_dest,version,verbose=False):
    self.v = verbose
    self.s = session
    self.ver = version
    self.t = tools
    self.d = "{0}reports/build/".format(st_dest)
    self.filename = ""

  def startDocument(self,title):
    macros = {'TITLE':title,
              'VER':self.ver}
    self.t.write_template(path=self.d,filename=self.filename,template="start_document.template",macros=macros,type='latex')

  def endDocument(self):
    self.t.write_template(path=self.d,filename=self.filename,template="end_document.template",macros={},type='latex')
    self.__exportPdf()

  def __exportPdf(self):
    fname = self.filename
    cwd = os.getcwd()
    os.chdir(self.d)
    os.environ["TEXINPUTS"] = '.:{0}/:'.format(self.t.get_latex_path())
    cmd = 'pdflatex {0}> {1} 2>&1'.format(fname,self.outname)
    cmd = 'pdflatex {0}'.format(fname)
    os.system(cmd)
    os.system(cmd)
    os.system(cmd)
    nfname = fname.replace('tex','pdf')
    cmd = 'mv {0} ../'.format(nfname)
    os.system(cmd)
    os.chdir(cwd)

  def crate_profile(self,ln):
    props = ln.get_ln_properties()
    macros = {}
    macros["ID"] = "LN{0}".format(props['lnid'])
    macros["INST"] = ""
    macros["LNID"] = "{0}".format(props["lnid"])
    macros["LOCATION"] = props["crate"]
    macros["SHM"] = props["shm"]
    macros["MPLN"] = props["p"]
    macros["S1A"] = "{0}".format(props['slot1']['app_text'])
    macros["S2T"] = "{0}".format(props['slot2']['type'])
    macros["S2A"] = "{0}".format(props['slot2']['app_text'])
    macros["S3T"] = "{0}".format(props['slot3']['type'])
    macros["S3A"] = "{0}".format(props['slot3']['app_text'])
    macros["S4T"] = "{0}".format(props['slot4']['type'])
    macros["S4A"] = "{0}".format(props['slot4']['app_text'])
    macros["S5T"] = "{0}".format(props['slot5']['type'])
    macros["S5A"] = "{0}".format(props['slot5']['app_text'])
    macros["S6T"] = "{0}".format(props['slot6']['type'])
    macros["S6A"] = "{0}".format(props['slot6']['app_text'])
    macros["S7T"] = "{0}".format(props['slot7']['type'])
    macros["S7A"] = "{0}".format(props['slot7']['app_text'])
    return macros
