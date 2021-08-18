import socket, sys
from ctypes import *

from mps_database.mps_config import MPSConfig, models
from mps_database.history.tools import history_tools


class Message(Structure):
    """
    Class responsible for defining messages coming from the Central Node IOC

    Fault ID is connected to only one device ID, can move backwords
    """
    _fields_ = [
        ("type", c_uint),
        ("id", c_uint),
        ("old_value", c_uint),
        ("new_value", c_uint),
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
        print(self.host)

        #self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        #self.sock.bind((self.host, self.port))
        
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.bind((self.host, self.port))
        
        except socket.error:
            print('Failed to create socket')
            sys.exit()
        

    def listen_socket(self):
        while True:
            self.receive_update()

    def receive_update(self):
        """
        Receives data from the socket, puts it into a message object, and sends it to the decoder
        """
        message=Message(0, 0, 0, 0, 0)
        
        data, ipAddr = self.sock.recvfrom(sizeof(Message))
        if data:
            print("Received\n", data)
            message = Message.from_buffer_copy(data)
            self.decode_message(message)
    

    #TODO: Ideally "it would be nice to log errors. For now, print
    def log_error(self, fault):
        print("ERROR: Unable to log entry in database")
        print("\t ", fault)
        return

    def decode_message(self, message):
        """
        Determines the type of the message, and sends it to the proper function for processing/including to the db
        """
        if (message.type == 1): # FaultStateType 
            self.history_db.add_fault(message)
        elif (message.type == 2): # BypassStateType
            self.history_db.add_bypass(message)
        elif (message.type == 4): # MitigationType
            self.history_db.add_mitigation(message)
        elif (message.type == 5): # DeviceInput (DigitalChannel)
            self.history_db.add_device(message)
        elif (message.type == 6): # AnalogDevice
            self.history_db.add_analog(message)
        else:
            self.log_error(message)

#host = socket.gethostname()
host = '127.0.0.1'
#host = "192.168.0.215"
port=1234

hist = HistoryServer(host, port)
hist.listen_socket()