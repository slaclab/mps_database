#!/usr/bin/env python

import socket
import argparse

UDP_IP = "134.79.216.240"
UDP_PORT = 4478


parser = argparse.ArgumentParser(description='Test script to request threshold restore')
parser.add_argument('--app-id', metavar='ID', type=int, help='application global id')
args = parser.parse_args()

#request = bytearray([100, 0, 0, 0, # restore request type
#                     args.app_id,  0, 0, 0, # app id
#                     0,   0, 0, 0, 
#                     0,   0, 0, 0,
#                     0,   0, 0, 0])
request = bytearray([100, 0, 0, 0, # restore request type
                     args.app_id&0xff, (args.app_id>>8)&0xff,
                     (args.app_id>>16)&0xff, (args.app_id>>24)&0xff,
                     0,   0, 0, 0, 
                     0,   0, 0, 0,
                     0,   0, 0, 0])


sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.sendto(request, (UDP_IP, UDP_PORT))
