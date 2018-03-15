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

import operator

# Supporting addition, subtraction, multiplication and division.

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
        usage()

def check_numeric(val, arg):
    try:
        value = int(val)
    except ValueError:
        print("-")
        print(val)
        print(arg + " must be an int")
        sys.exit(1)

def send(local_port, poc_name, poc_port, num_of_ringos):
    server_address = (poc_name, int(poc_port))  # server address
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    while True:
        sendData = input("> ")
        if sendData is None:
            break

        # send the request
        client_socket.sendto(
            sendData.encode('utf-8'),
            server_address)

# Peer Rescovery
### put it on ringo lists, keep them asking for the neighbors. Let them know asking for header.
### == whatevers. check header.

def forward(local_port, poc_name, poc_port, num_of_ringos):
    print('Forwarder')
    # Forwarder Peer Discovery


# Not YET
def handle_incoming_data(data, peer_ip, peer_port):
    json_obj = json.loads(data)
    keyword = json_obj['command']
    # print(keyword)

def receive(local_port, poc_name, poc_port, num_of_ringos):
    host = "127.0.0.1"
    # AF_INET: Internet Iv4
    # SOCK_DGRAM: UDP Protocol
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((host, int(local_port)))

    while True:
        data, addr = server_socket.recvfrom(1024)
        data = data.decode('utf-8')

        client_thread = Thread(target=handle_incoming_data, args=(data, addr[0], addr[1]))
        client_thread.start()

        print('message from user: ' + str(addr))
        print('from connected user: ' + data)

    # Close the Socket
    server_socket.close()

def main():
    if (len(sys.argv) != 6):
        usage()

    # python3 ringo.py S 100.0 john 90 90
    # Interpret the argument
    flag = sys.argv[1] # Getting a flag i.e) S, F, R
    local_port = sys.argv[2] # Getting a local port i.e) 23222
    poc_name = sys.argv[3] # Getting the port name i.e) networklab3.cc.gatech.edu
    poc_port = sys.argv[4] # Getting the port number i.e) 8080 or 13445
    num_of_ringos = sys.argv[5] # Getting the number of ringos i.e) 5

    # Define RTT Table
    peers = {}

    # Checking if we get the right argument types
    check_flag(flag);
    check_numeric(local_port, "local-port");
    check_numeric(poc_port, "PoC-port");
    check_numeric(num_of_ringos, "N");

    ###### Peer Discover Here. #
    this_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    host = "127.0.0.1"
    print(local_port)
    this_socket.bind((host, int(local_port)))

    while True:
        print('loop')
        print(len(peers))
        print(num_of_ringos)
        if len(peers) == int(num_of_ringos):
            # the length of rtt_table is N, break!.
            print('break')
            break
        # send our rtt table to poc (if it has a PoC)
        if poc_name != "0":
            poc_address = (poc_name, int(poc_port))
            peers[str(poc_address)] = 1 # should be peer information though..
            print("here")
            print(peers)
            peer_data = json.dumps({
                'command': 'peer_discovery',
                'peers': peers})
            this_socket.sendto(
                peer_data.encode('utf-8'),
                poc_address)

        # Receive the response from PoC
        data, addr = this_socket.recvfrom(1024)
        peers[str(addr)] = 1 # add sender address to its peers

        data = data.decode('utf-8')
        print(data)
        json_obj = json.loads(data)
        keyword = json_obj['command']
        peers_response = json_obj['peers']
        if keyword == "peer_discovery":
            # we REPLY the peers
            print("=====")
            print('print')
            print(peers)
            print(peers_response)
            print('--')
            for key in peers_response:
                peers[key] = 1
            print(peers)
            new_peer_data = json.dumps({
                'command': 'peer_discovery',
                'peers': peers})
            print('what is new peer data')
            print(peers)
            this_socket.sendto(
                new_peer_data.encode('utf-8'),
                addr)


    this_socket.close()
    # print('End of Peer Discovery')
    print('Peers List: ')
    print(peers)


    # QUESTION: We can open the Command Line interface HERE?
    # interface_thread = Thread(target = open_interface, args=())
    # interface_thread.start()


    # QUESTION: Register PoC HERE for its neighbor????

    # flag, local_port, poc_name, poc_port, num_of_ringos
    # If it's a Receiver
    # if flag == "R":
    #     receive(local_port, poc_name, poc_port, num_of_ringos)
    #
    # # If it's forwarder
    # elif flag == "F":
    #     forward(local_port, poc_name, poc_port, num_of_ringos)
    #
    # # If it's sender
    # elif flag == "S":
    #     send(local_port, poc_name, poc_port, num_of_ringos)

if __name__ == "__main__":
    main();
