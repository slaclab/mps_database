#!/usr/bin/env python
from mps_database.mps_config import MPSConfig,models
from sqlalchemy import MetaData
import yaml
from yaml import MappingNode, ScalarNode
from sqlalchemy import Column, Integer, Float, String, Boolean
import math


class ExportDisplays():

  def __init__(self,session,tools,st_dest,version,verbose=False):
    self.v = verbose
    self.s = session
    self.ver = version
    self.t = tools
    self.d = st_dest
    self.display_path = '{}display/'.format(st_dest)

  def export(self):
    link_nodes = self.s.query(models.LinkNode).all()
    for ln in link_nodes:
      self.generate_crate_display(ln)
      self.generate_input_display(ln)
    for a in self.t.lclshome_areas.keys():
      link_nodes = self.s.query(models.LinkNode).join(models.LinkNode.crate)\
      .filter(models.Crate.area.in_(self.t.lclshome_areas[a])).order_by(models.LinkNode.lnid).all()
      self.generate_area_display(a,link_nodes)
    for g in self.s.query(models.LinkNodeGroup).order_by(models.LinkNodeGroup.number).all():
      self.generate_group_display(g)
    self.generate_cn_status_display(self.s.query(models.LinkNodeGroup).order_by(models.LinkNodeGroup.number).all())

  def generate_cn_status_display(self,groups):
    global_macros = []
    for g in groups:
      for ln in g.link_nodes:
        props = ln.get_ln_properties()
        for slot in range(1,8):
          key = "slot{0}".format(slot)
          if props[key]['used']:
            macros = {}
            macros['GROUP'] = "{0}".format(props["group"])
            macros['LN'] = "{0}".format(props["lnid"])
            macros['SLOT'] = props[key]["slot_text"]
            macros['APP'] = props[key]["app_text"]
            macros['P'] = props[key]["p"]
            macros['CRATE'] = props["crate"]
            macros['CN'] = props["CN"]
            global_macros.append(macros)
    filename = '{0}status/cn_status.json'.format(self.display_path)
    self.t.write_json_file(filename, global_macros)

  def generate_input_display(self,ln):
    props = ln.get_ln_properties()
    filename = '{0}inputs/ln_{1}_inputs.json'.format(self.display_path,props['lnid'])
    disp_macros = []
    for slot in range(1,8):
      key = "slot{0}".format(slot)
      if props[key]['used']:
        app_filename = '{0}thresholds/app{1}{2}.json'.format(self.display_path,props[key]["app"],props[key]["input_fn"])
        app_macros = []
        for ch in props[key]["card"].channels:
          c_props = ch.get_channel_properties()
          for cp in c_props:
            macros = {}
            macros['CRATE'] = cp["CRATE"]
            macros['SLOT'] = cp["SLOT"]
            macros['DEVICE'] = cp["DEVICE"]
            macros['CHANNEL'] = cp["CHANNEL"]
            macros['DEVICE_BYP'] = cp["DEVICE_BYP"]
            macros['APPID'] = cp["APPID"]
            disp_macros.append(macros)
            macros = {}
            macros['P'] = props[key]["p"]
            macros['CH'] = cp["CH"]
            macros['DEVICE_NAME'] = cp["NAME"]
            macros['PV_PREFIX'] = cp["NAME"]
            macros['VIS'] = '{0}'.format(1)
            macros['DEVICE_THR'] = cp["NAME"]
            macros['FILE'] = ""
            app_macros.append(macros)
        self.t.write_json_file(app_filename,app_macros)
    self.t.write_json_file(filename,disp_macros)


  def generate_crate_display(self,ln):
    width = 347
    header_height = 30
    widget_height = 20
    height = header_height + widget_height * 8 + 5
    props = ln.get_ln_properties()
    slots_path = '{0}slots/'.format(self.display_path)
    filename = 'LinkNode{0}_slot.ui'.format(props['lnid'])
    macros = { 'HEADER_HEIGHT':'{0}'.format(int(header_height)),
               'WIDTH':'{0}'.format(int(width)),
               'HEIGHT':'{0}'.format(int(height)),
               'P':'{0}:1'.format(props['p']) }
    self.__write_crate_header(path=slots_path,name=filename,macros=macros)
    x = 5
    for s in range(1,8):
      y = header_height + s*widget_height
      key = "slot{0}".format(s)
      slot = props[key]
      if slot["used"]:
        macros = {'SLOT':slot['slot_text'],
                  'CN':props['CN'],
                  'AID':slot['app_text'],
                  'MPS_PREFIX':slot['p'],
                  'TYPE':slot['short_name'],
                  'X':'{0}'.format(int(x)),
                  'Y':'{0}'.format(int(y)),
                  'POSTFIX':slot['postfix'],
                  'FILENAME':slot['display_fn'],
                  'IOC':slot['ioc'],
                  'ALARM':slot['alarm'],
                  'LOCA':props['area'],
                  'IOC_UNIT':props['location'],
                  'INST':slot['inst']}
        self.__write_crate_embed(path=slots_path,name=filename,macros=macros)
      else:
        macros = {'SLOT':'2',
                'X':'{0}'.format(int(x)),
                'Y':'{0}'.format(int(y))}
        self.__write_crate_empty(path=slots_path,name=filename,macros=macros)
    self.__write_crate_footer(path=slots_path,name=filename,macros=macros)

  def generate_area_display(self,area,link_nodes):
      header_height = 30
      height = int(header_height + (len(link_nodes)*30))
      macros = { 'HEIGHT':'{0}'.format(int(height))}
      area_path = '{0}areas/'.format(self.display_path)
      filename = 'mps_{0}_link_nodes.ui'.format(area.lower())
      self.__write_area_header(path=area_path,name=filename,macros=macros)
      y = header_height
      groups = []
      for ln in link_nodes:
        props = ln.get_ln_properties()
        macros = {}
        macros["Y"] = "{0}".format(int(y))
        macros["PREFIX"] = "{0}:1".format(props["p"])
        macros["LN_ID"] = "{0}".format(props["lnid"])
        macros["SLOT_FILE"] = 'LinkNode{0}_slot.ui'.format(props["lnid"])
        macros["LOCA"] = props["area"]
        macros["IOC_UNIT"] = props["location"]
        macros["INST"] = '{0}'.format(1)
        self.__write_area_embed(path=area_path,name=filename,macros=macros)
        if ln.group not in groups:
          groups.append(ln.group)
        y += 30
      self.__write_area_footer(path=area_path,name=filename,macros=macros)

  def generate_group_display(self,group):
    path = '{0}groups/'.format(self.display_path,group)
    filename = 'LinkNodeGroup{0}.ui'.format(group.number)
    header_height = 50
    footer_height = 51
    embedded_width = 457
    embedded_height = 230
    extra = 10
    max_width = 2000
    fudge = 0
    last_y = header_height
    rows = 1
    lns = group.link_nodes
    flns = group.find_first_lns()
    last_ln = group.find_last_ln()
    split_ln_location = ''
    last_ln_location = last_ln.crate.location
    len0 = len(lns)
    len1 = len(lns)
    if len(flns) > 1:
      rows = 2
      last_y = last_y + embedded_height/2
      split_lns = group.find_split_lns()
      if len(split_lns) > 1:
        print("ERROR: SW needs an update")
      else:
        split_ln_location = split_lns[0].crate.location
        len0 = group.build_ln_chain(flns[0])['length']
        len1 = group.build_ln_chain(flns[1])['length']
        if len0 < len1:
          tFln = flns[0]
          flns[0] = flns[1]
          flns[1] = tFln
          tlen = len1
          len1 = len0
          len0 = tlen
        window_width = max(len0,len1) * embedded_width + extra * 2
    else:
      window_width = len(lns) * embedded_width+extra*2
      if window_width > max_width:
        last_y = last_y + embedded_height
        rows = 2
        window_width = int((math.floor(len(lns)/2)+1) * embedded_width + extra * 2)
        fudge = int(embedded_width / 2)
        if len(lns) % 2 == 0:
          window_width = int((math.floor(len(lns)/2)) * embedded_width + extra * 2)
          fudge = 0
    window_height = header_height + footer_height + rows*embedded_height
    last_x = window_width - embedded_width - extra - fudge
    macros = { 'WIDTH':'{0}'.format(int(window_width)),
               'HEIGHT':'{0}'.format(int(window_height)),
               'TITLE':'SC Linac MPS Link Node Group {0}'.format(group.number) }
    self.__write_group_header(path=path,name=filename,macros=macros)
    row = 0
    node = 0
    for fln in flns:
      y = row * embedded_height + header_height
      chain = group.build_ln_chain(fln)
      for c in range(chain['length']):
        x = extra + node*embedded_width
        if x > window_width-embedded_width:
          node = 0
          x = extra + fudge
          y = embedded_height + header_height
        key = "{0}".format(c+1)
        props = chain[key].get_ln_properties()
        if props['crate'] != split_ln_location or props['crate'] != last_ln_location:
          if props['crate'] != last_ln_location:
            self.write_group_embed(props,x,y,path,filename)
        node = node+1
      row = row+1
      node = len0-len1
    props = last_ln.get_ln_properties()
    self.write_group_embed(props,last_x,last_y,path,filename)

    y = window_height-footer_height-1
    buttonx = int(window_width/2-100)
    buttony = y + 12
    macros = { 'BUTTON_X':'{0}'.format(int(buttonx)),
               'BUTTON_Y':'{0}'.format(int(buttony)),
               'Y':'{0}'.format(int(y)) }
    self.__write_group_end(path=path,name=filename,macros=macros)


  def write_group_embed(self,ln,x,y,path,filename):
    macros = { 'P':'{0}'.format(ln['ln_p']),
               'CN':'{0}'.format(ln['CN']),
               'AID':'{0}'.format(ln['daid']),
               'SLOT_FILE':'LinkNode{0}_slot.ui'.format(ln['lnid']),
               'P_IN':'{0}'.format(ln['p_next']),
               'X':'{0}'.format(int(x)),
               'Y':'{0}'.format(int(y)),
               'PGP':'{0}'.format(ln['rx_pgp']),
               'LN':'{0}'.format(ln['lnid']),
               'TYPE':'LOC',
               'LOCA':'{0}'.format(ln['area']),
               'IOC_UNIT':'{0}'.format(ln['location']),
               'INST':'{0}'.format(1),
               'TEXT':'{0}'.format(ln['disp_text'])}
    self.__write_group_embed(path=path,name=filename,macros=macros)

  def __write_area_header(self,path,name,macros):
      self.t.write_template(path=path,filename=name,template="ln_area_header.tmpl",macros=macros,type='display')

  def __write_area_footer(self,path,name,macros):
      self.t.write_template(path=path,filename=name,template="ln_area_footer.tmpl",macros=macros,type='display')

  def __write_area_embed(self,path,name,macros):
      self.t.write_template(path=path,filename=name,template="ln_area_embed.tmpl",macros=macros,type='display')

  def __write_crate_header(self,path,name,macros):
      self.t.write_template(path=path,filename=name, template="ln_crate_header.tmpl", macros=macros,type='display')

  def __write_crate_embed(self,path,name,macros):
      self.t.write_template(path=path,filename=name, template="ln_crate_embed.tmpl", macros=macros,type='display')
  
  def __write_crate_empty(self,path,name,macros):
      self.t.write_template(path=path,filename=name, template="ln_crate_empty.tmpl", macros=macros,type='display')

  def __write_crate_footer(self,path,name,macros):
      self.t.write_template(path=path,filename=name, template="ln_crate_footer.tmpl", macros=macros,type='display')

  def __write_group_header(self,path,name,macros):
      self.t.write_template(path=path,filename=name,template="ln_group_header.tmpl",macros=macros,type='display')

  def __write_group_embed(self,path,name,macros):
      self.t.write_template(path=path,filename=name,template="link_node_group_embedded_display.tmpl",macros=macros,type='display')

  def __write_group_end(self,path,name,macros):
      self.t.write_template(path=path,filename=name,template="ln_group_end.tmpl",macros=macros,type='display')

