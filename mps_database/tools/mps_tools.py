#!/usr/bin/env python
from mps_database.mps_config import MPSConfig, models
from sqlalchemy import MetaData
import os
import errno
import shutil
import re

class MpsTools:
  def __init__(self,verbose=False):
    self.v = verbose
    self.non_link_node_types = ["BPMS", "BLEN", "FARC", "TORO", "WIRE"]
    self.lc1_areas = ["CLTS","BSYS","BSYH","LTUS","LTUH","UNDS","UNDH","FEES","FEEH","LTU0","UND0","BSY0","DMP0","DMPH","DMPS"]
    self.hard_areas = ['BSYH','LTUH','UNDH','DMPH','FEEH']
    self.soft_areas = ['CLTS','BSYS','LTUS','UNDS','FEES','DMPS']
    self.sc_areas = ['GUNB','L0B','HTR','EMIT2','COL0','COL1','BC1B','BC2B','L2B','L3B','DOG','BPN13','BPN14','BPN15','BPN16','BPN17','BPN18','BPN19','BPN20',
                     'BPN21','BPN22','BPN23','BPN24','BPN25','BPN26','BPN27','BPN28','SPD','SLTD']
    #self.template_path = 'templates/'

  def create_dir(self,path,clean=False):
    """
    Create a new directory into a specified path.

    If the directory already exists and the 'clean' flag is true,
    then the directory will be removed, and then recreated; otherwise
    the directory will not be created.

    If 'verbose' is true, them debug messages with information will be
    displayed.
    """

    #if path[-1] != '/':
    #  path = "{0}/".format(path)
    dir_name = os.path.dirname(path)
    dir_exist = os.path.exists(dir_name)
    if clean and dir_exist:
      if self.v:
        print(("Directory '{}' exists. Removing it...".format(dir_name)))
      shutil.rmtree(dir_name, ignore_errors=True)
      dir_exist = False
    if not dir_exist:
      if self.v:
        print(("Directory '{}' does not exist. Creating it...".format(dir_name)))
      try:
        os.makedirs(dir_name)
        if self.v:
          print("Directory created.")
      except OSError as exc: # Guard against race condition
        if exc.errno != errno.EEXIST:
          raise

  def get_template_path(self):
      full_path_split = os.path.realpath(__file__).split('/')[:-2 or None]
      full_path_split.append('templates/')
      return '/'.join(full_path_split)

  def get_latex_path(self):
      full_path_split = os.path.realpath(__file__).split('/')[:-2 or None]
      full_path_split.append('templates/')
      full_path_split.append("latex/")
      return '/'.join(full_path_split)

  def write_template(self,path,filename,template,macros,type):
      file = "{0}{1}".format(path,filename)
      template = "{0}{1}/{2}".format(self.get_template_path(),type,template)
      self.write_file_from_template(file=file, template=template, macros=macros)

  def write_file_from_template(self, file, template, macros):
      """
      Genetic method to write a file from a template, substituting the
      passed macro definitions.

      The output file is opened in append mode, so calling this function
      pointing to the same file will add content to the file.

      If the directory of the output file does not exist, it will be created.
      """
      self.create_dir(file)
      with open(file, 'a') as db, open(template, 'r') as template:
          for line in template:
              db.write(self.__expand_macros(line, macros))

  def __expand_macros(self, text, macros):
      """
      Generic method to substitute macros in a block of text.

      The macros are defined in a dictionary, where the keys are the macro
      and the value is the string to substitute it. The macros in the text
      and defined as $(MACRO_NAME), where only MACRO_NAME is the key string
      in the dictionary.

      It will return the original text will all the macros found in it
      substituted by the respective values.
      """
      for k, v in list(macros.items()):
          text = re.sub(r'\$\(({key}|{key},[^)]*)\)'.format(key=k),v, text)

      return text

  def is_lc1(self,area):
    if area in self.lc1_areas:
      return True
    else:
      return False