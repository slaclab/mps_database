import socket, sys
from ctypes import *

from mps_database.mps_config import MPSConfig, models
from mps_database.history import history_tools


class Message(Structure):
    """
    Class responsible for defining messages coming from the Central Node IOC

    Fault ID is connected to only one device ID, can move backwords
    """
    _fields_ = [
        ("type", c_uint),
        ("id", c_uint),
        ("oldValue", c_uint),
        ("newValue", c_uint),
        ("aux", c_uint),
        ]

class HistoryServer:
    """
    Most of this class has been taken from the depreciated EicHistory.py server. 
    """
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = None

        self.history_db = history_tools.HistorySession()
              # create dgram udp socket
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        except socket.error:
            print('Failed to create socket')
            sys.exit()

    def receive_update(self):
        """
        Receives data from the socket, puts it into a message object, and sends it to the decoder
        """
        message=Message(0, 0, 0, 0, 0)
        data, ipAddr = self.sock.recvfrom(sizeof(Message))
        if data:
            message = Message.from_buffer_copy(data)
            self.decode_message(message)

    #TODO: Ideally it would be nice to log errors. For now, print
    def log_error(self, fault):
        print("ERROR: Unable to log entry in database")
        print("\t ", fault)
        return

    #TODO: do I need any of these? ask jeremy
    def decode_message(self, message):
        """
        Determines the type of the message, and sends it to the proper function for processing/including to the db
        """
        if (message.type == 1): # FaultStateType
            
            self.history_db.add_fault(message)
            #self.printFault(message)
        elif (message.type == 2): # BypassStateType
            #self.printBypassState(message)
            pass
        elif (message.type == 4): # MitigationType
            #self.printMitigation(message)
            pass
        elif (message.type == 5): # DeviceInput (DigitalChannel)
            #self.printDeviceInput(message)
            pass
        elif (message.type == 6): # AnalogDevice
            #self.printAnalogDevice(message)
            pass
        else:
            self.log_error(message)

# <-------------------------------------------   Old funcs for reference


    def printFault(self, message):
        messageType = "FAULT"
        try:
            #Get the fault id from the configure db
            fault = self.history.conf_conn.session.query(models.Fault).filter(models.Fault.id==message.id).first()
            #TODO: what is aux? Why do we need the device state? Do we want the model of listing both okay to faulted?
            #TODO: is there a faulted to okay message we need to include as well?
            if message.aux > 0:
                deviceState = self.history.conf_conn.session.query(models.DeviceState).filter(models.DeviceState.id==message.aux).first()

            newState = "OK"
            if message.newValue == 1:
                newState = "FAULTED"
                
            #Add Description, change, and the device state
            #TODO: do we want device state?
            if message.aux > 0:
                messageString = '{0}: -> {1} ({2})'.format(fault.description, newState, deviceState.name)
            else:
                messageString = '{0}: -> {1}'.format(fault.description, newState)
    
            #Print the actual message
            self.printMessage(messageType, messageString)

        #Error Checking for bad message format - TODO: what do we do here?
        except Exception as ex:
            print(ex)
            self.printGeneric(messageType, message)

    def printDeviceInput(self, message):
        messageType = "INPUT"
        try:
            deviceInput = self.history.conf_conn.session.query(models.DeviceInput).filter(models.DeviceInput.id==message.id).first()
            channel = self.history.conf_conn.session.query(models.DigitalChannel).filter(models.DigitalChannel.id==deviceInput.channel_id).first()
            device = self.history.conf_conn.session.query(models.DigitalDevice).filter(models.DigitalDevice.id==deviceInput.digital_device_id).first()

            oldName = channel.z_name
            newName = channel.z_name
            if (message.oldValue > 0):
                oldName = channel.o_name
            if (message.newValue > 0):
                newName = channel.o_name

            messageString = '{0} [{3}]: {1} -> {2}'.format(channel.name, oldName, newName, device.name)
            self.printMessage(messageType, messageString)

        except:
            self.printGeneric(messageType, message)

    def printBypassState(self, message):
        messageType = "BYPAS"
        try:
            if (message.aux > 31) :
                deviceInput = self.session.query(models.DeviceInput).filter(models.DeviceInput.id==message.id).first()
                channel = self.session.query(models.DigitalChannel).filter(models.DigitalChannel.id==deviceInput.channel_id).first()
            else:
                analogDevice = self.session.query(models.AnalogDevice).filter(models.AnalogDevice.id==message.id).first()
                channel = self.session.query(models.AnalogChannel).filter(models.AnalogChannel.id==analogDevice.channel_id).first()

            if (message.oldValue == 0):
                oldName = "Valid"
            else:
                oldName = "Expired"

            if (message.newValue == 0):
                newName = "Valid"
            else:
                newName = "Expired"

            if (message.aux > 31) :
                messageString = '{0}: {1} -> {2}'.format(channel.name, oldName, newName)
            else:
                messageString = '{0}: {1} -> {2} (integrator {3})'.format(channel.name, oldName, newName, message.aux)

            self.printMessage(messageType, messageString)
        except:
            self.printGeneric(messageType, message)
# <-------------------------------------------   Old funcs for reference


