#!/usr/bin/env python

class CnStatusDisplay:
  def __init__(self):
    self.macros = []

  def add_macros(self,macros):
    self.macros.append(macros)

  def get_macros(self):
    return self.macros
