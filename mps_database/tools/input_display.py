#!/usr/bin/env python
from mps_database.mps_config import MPSConfig, models, runtime
from sqlalchemy import MetaData
from mps_database.tools.mps_names import MpsName
from mps_database.tools.mps_reader import MpsReader, MpsDbReader
from latex import Latex
import math
import argparse
import time
import yaml
import os
import sys

class InputDisplay:
  def __init__(self, ln):
    self.ln = ln
    self.macros = []
    self.input_report_rows = []
    self.digital_ln_macros = []
    self.bay0_macros = []
    self.bay1_macros = []

  def add_macros(self,macros):
    self.macros.append(macros)

  def get_macros(self):
    return self.macros

  def append_row(self,row):
    self.input_report_rows.append(row)

  def get_input_report_rows(self):
    return self.input_report_rows

  def add_digital_ln_macros(self,macros):
    self.digital_ln_macros.append(macros)
  
  def get_digital_ln_macros(self):
    return self.digital_ln_macros

  def reset_digital_ln_macros(self):
    self.digital_ln_macros = []

  def add_analog_macros(self,macros,bay):
    if bay == 0:
      self.bay0_macros.append(macros)
    else:
      self.bay1_macros.append(macros)

  def reset_analog_macros(self):
    self.bay0_macros = []
    self.bay1_macros = []

  def get_analog_macros(self,bay):
    if bay == 0:
      return self.bay0_macros
    else:
      return self.bay1_macros 

