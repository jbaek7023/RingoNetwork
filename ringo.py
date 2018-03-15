# RDT Ringo
#
# a Ringo node using the Reliable Data Transfer protocol, using skeletal code based on
# socket_echo_server_dgram.py and socket_echo_client_dgram.py from https://pymotw.com/3/socket/udp.html

import socket
import sys
from threading import Thread
from datetime import datetime
import time
import json

def usage():
    print ("Usage: python ringo.py <flag> <local-port> <PoC-name> <PoC-port> <N>")
    sys.exit(1)

def check_flag(role):
    if (sys.argv[1]=="S"):
        role = "S"
    elif (sys.argv[1]=="F"):
        role = "F"
    elif (sys.argv[1]=="R"):
        role = "R"
    else:
        usage();

def check_numeric(val, arg):
    try:
        value = int(val)
    except ValueError:
        print("-")
        print(val)
        print(arg + " must be an int")
        sys.exit(1)

def main():
    if (len(sys.argv) != 6):
        usage();

    # python3 ringo.py S 100.0 john 90 90
    # Interpret the argument
    flag = sys.argv[1] # Getting a flag i.e) S, F, R
    local_port = sys.argv[2] # Getting a local port i.e) 23222
    poc_name = sys.argv[3] # Getting the port name i.e) networklab3.cc.gatech.edu
    poc_port = sys.argv[4] # Getting the port number i.e) 8080 or 13445
    num_of_ringos = sys.argv[5] # Getting the number of ringos i.e) 5

    # Define RTT Table
    rtt = {}

    # Checking if we get the right argument types
    check_flag(flag);
    check_numeric(local_port, "local-port");
    check_numeric(poc_port, "PoC-port");
    check_numeric(num_of_ringos, "N");

    # QUESTION: We should perform Peer Discovery Here?


    # QUESTION: We can open the Command Line interface HERE?
    # interface_thread = Thread(target = open_interface, args=())
    # interface_thread.start()


    # QUESTION: Register PoC HERE for its neighbor????


    # If it's a Receiver
    if flag == "R":
        # Creates a serve socket and connect to the
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        host = "127.0.0.1" # local host because it's server
        server_socket.bind((host, local_port))

        while 1:
            data, addr = server_socket.recvfrom(4086)
            # QUESTION: we're going to handle incoming data here?
            # client_thread = Thread(target=handle_incoming_data, args=(data, addr[0], add[1]))
            # client_thread.start()

    # If it's forwarder
    elif flag == "F":
        print('Forwarder')
        # server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # host = "127.0.0.1" # local host because it's server
        # server_socket.bind((host, local_port))

    # If it's sender
    elif flag == "S":
        print("Sender")

if __name__ == "__main__":
    main();
