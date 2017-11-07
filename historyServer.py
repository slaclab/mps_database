#!/usr/bin/env python

import socket
import sys
import os
import argparse
import time

from mps_config import MPSConfig, models

from ctypes import *
    
class Message(Structure):
    _fields_ = [
        ("type", c_uint),
        ("id", c_uint),
        ("oldValue", c_uint),
        ("newValue", c_uint),
        ("aux", c_uint),
        ]

def printGeneric(messageType, message):
    print messageType + "type=" + str(message.type) + ", id=" + str(message.id) + ", old=" + str(message.oldValue) + ", new=" + str(message.newValue) + ", aux=" + str(message.aux)

def printMitigation(message, session):
    try:
        device = session.query(models.MitigationDevice).filter(models.MitigationDevice.id==message.id).first()
        bc1 = session.query(models.BeamClass).filter(models.BeamClass.id==message.oldValue).first()
        bc2 = session.query(models.BeamClass).filter(models.BeamClass.id==message.newValue).first()

        print "[MITGN]\t" + device.name + ": " + bc1.name + " -> " + bc2.name
        
    except:
        printGeneric(message)

def printFault(message, session):
    messageType = "[FAULT]\t"
    try:
        fault = session.query(models.Fault).filter(models.Fault.id==message.id).first()
        if message.aux > 0:
            deviceState = session.query(models.DeviceState).filter(models.DeviceState.id==message.aux).first()

        newState = "OK"
        if message.newValue == 1:
            newState = "FAULTED"
            
        if message.aux > 0:
            print messageType + fault.description + ": -> " + newState + " (" + deviceState.name + ")"
        else:
            print messageType + fault.description + ": -> " + newState

    except:
        printGeneric(messageType, message)

def printBypassState(message, session):
    messageType = "[BYPAS]\t"
    try:
        if (message.aux > 31) :
            deviceInput = session.query(models.DeviceInput).filter(models.DeviceInput.id==message.id).first()
            channel = session.query(models.DigitalChannel).filter(models.DigitalChannel.id==deviceInput.channel_id).first()
        else:
            analogDevice = session.query(models.AnalogDevice).filter(models.AnalogDevice.id==message.id).first()
            channel = session.query(models.AnalogChannel).filter(models.AnalogChannel.id==analogDevice.channel_id).first()

        if (message.oldValue == 0):
            oldName = "Valid"
        else:
            oldName = "Expired"

        if (message.newValue == 0):
            newName = "Valid"
        else:
            newName = "Expired"

        if (message.aux > 31) :
            print messageType + channel.name + ": " + oldName + " -> " + newName
        else:
            print messageType + channel.name + ": " + oldName + " -> " + newName + " (integrator " + str(message.aux) + ")"

    except:
        printGeneric(messageType, message)

def printDeviceInput(message, session):
    messageType = "[INPUT]\t"
    try:
        deviceInput = session.query(models.DeviceInput).filter(models.DeviceInput.id==message.id).first()
        channel = session.query(models.DigitalChannel).filter(models.DigitalChannel.id==deviceInput.channel_id).first()

        oldName = channel.z_name
        newName = channel.z_name
        if (message.oldValue > 0):
            oldName = channel.o_name
        if (message.newValue > 0):
            newName = channel.o_name

        print messageType + channel.name + ": " + oldName + " -> " + newName

    except:
        printGeneric(messageType, message)

def printAnalogDevice(message, session):
    messageType = "[INPUT]\t"
    try:
        analogDevice = session.query(models.AnalogDevice).filter(models.AnalogDevice.id==message.id).first()
        channel = session.query(models.AnalogChannel).filter(models.AnalogChannel.id==analogDevice.channel_id).first()

        print messageType + channel.name + ": " + hex(message.oldValue) + " -> " + hex(message.newValue)

    except:
        printGeneric(messageType, message)


def decodeMessage(message, session):
    if (message.type == 1): # FaultStateType
        printFault(message, session)
    elif (message.type == 2): # BypassStateType
        printBypassState(message, session)
    elif (message.type == 4): # MitigationType
        printMitigation(message, session)
    elif (message.type == 5): # DeviceInput (DigitalChannel)
        printDeviceInput(message, session)
    elif (message.type == 6): # AnalogDevice
        printAnalogDevice(message, session)
    else:
        printGeneric("[?????]\t", message)

def receiveUpdate(sock, session):
    message=Message(0, 0, 0, 0, 0)
    data, ipAddr = sock.recvfrom(sizeof(Message))
    if data:
        message = Message.from_buffer_copy(data)
        decodeMessage(message, session)

parser = argparse.ArgumentParser(description='Receive MPS status messages')
parser.add_argument('--host', metavar='hostname', type=str, nargs=1, help='Central node hostname')
parser.add_argument('--port', metavar='port', type=int, nargs='?', help='server port (default=3356)')
parser.add_argument('database', metavar='db', type=file, nargs=1,
                    help='database file name (e.g. mps_gun_config.db)')


args = parser.parse_args()

 # create dgram udp socket
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
except socket.error:
    print 'Failed to create socket'
    sys.exit()
 
if args.host:
    host = args.host[0]
else:    
    host = 'lcls-dev3'

port=3356
if args.port:
    port = args.port

myAddr = (host, port)
sock.bind(myAddr)

mps = MPSConfig(args.database[0].name)
session = mps.session

done = False
print "=== History Server ==="
while not done:
    receiveUpdate(sock, session)

session.close()
