import socket, sys, argparse, datetime, errno
from ctypes import *

from mps_database.mps_config import MPSConfig, models
from mps_database.history.tools import history_tools, logger


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
    
    def to_string(self):
        return str(self.type) + " " + str(self.id) + " " + str(self.old_value) + " " + str(self.new_value) + " " + str(self.aux) 

class HistoryServer:
    """
    Most of this class has been taken from the depreciated EicHistory.py server. 
    """
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = None
        self.logger = logger.Logger(stdout=True)

        self.history_db = history_tools.HistorySession()
              # create dgram udp socket
        
        print(self.host)

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.bind((self.host, self.port))
        
        except socket.error:
            self.logger.log("SOCKET ERROR: Failed to create socket")
            self.logger.log("Exiting -----")
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
            print("Message\n", message.type, message.id, message.old_value, message.new_value, message.aux)
            self.decode_message(message)
    
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
            self.history_db.add_input(message)
        elif (message.type == 6): # AnalogDevice
            self.history_db.add_analog(message)
        else:
            self.logger.log("DATA ERROR: Bad Message Type", message.to_string())

def main():

    parser = argparse.ArgumentParser(description='Receive MPS history messages')
    parser.add_argument('--port', metavar='port', type=int, nargs='?', help='server port (default=3356)')
    parser.add_argument('--database', metavar='db', nargs=1, default='mps_gun_history.db', 
                        help='database file name (e.g. mps_gun_history.db)')
    args = parser.parse_args()

    #host = socket.gethostname()
    host = '127.0.0.1'

    #Set default port number
    if args.port:
        port = args.port
    else:    
        port=1234

    hist = HistoryServer(host, port)
    hist.listen_socket()                        
    return


if __name__ == "__main__":
    main()