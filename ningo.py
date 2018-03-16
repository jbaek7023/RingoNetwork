# RDT Ringo
#
# a Ringo node using the Reliable Data Transfer protocol, using skeletal code based on
# socket_echo_server_dgram.py and socket_echo_client_dgram.py from https://pymotw.com/3/socket/udp.html

import socket
import socketserver
import sys
from threading import Thread
from datetime import datetime
import time
import json
import timeit
import ast

# Supporting addition, subtraction, multiplication and division.
peers = {}
rtt_matrix = {}

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
        print(arg + " must be an int")
        sys.exit(1)


# Peer Forwarder
# def forward(local_port, poc_name, poc_port, num_of_ringos):
#     print('Forwarder')
#     # Forwarder Peer Discovery
#
#
# # Not YET
# def handle_incoming_data(data, peer_ip, peer_port):
#     json_obj = json.loads(data)
#     keyword = json_obj['command']
#     # print(keyword)
#
# def receive(local_port, poc_name, poc_port, num_of_ringos):
#     host = "127.0.0.1"
#     # AF_INET: Internet Iv4
#     # SOCK_DGRAM: UDP Protocol
#     server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#     # server_socket.bind((host, int(local_port)))
#
#     while True:
#         data, addr = server_socket.recvfrom(1024)
#         data = data.decode('utf-8')
#         client_thread = Thread(target=handle_incoming_data, args=(data, addr[0], addr[1]))
#         client_thread.start()
#
#         print('message from user: ' + str(addr))
#         print('from connected user: ' + data)
#
#     # Close the Socket
#     server_socket.close()


class MyUDPHandler(socketserver.BaseRequestHandler):
    def handle(self):
        data = self.request[0]
        socketo = self.request[1]
        # self.client_address[0] : 127.0.0.1
        # self.client_address[0] : 12443 port.
        # print(data.decode("utf-8"))
        json_obj = json.loads(data.decode("utf-8"))
        keyword = json_obj.get('command')
        peers_response = json_obj.get('peers')

        if keyword == "peer_discovery":
            peers[str(self.client_address)] = 1  # Add to the Peer List

            for key in peers_response:
                peers[key] = 1
            new_peer_data = json.dumps({
                'command': 'peer_discovery',
                'peers': peers,
                'ttl': json_obj['ttl'] - 1,
            })

            if 'ttl' in json_obj: # or json_obj['peers'] < num_of_ringos: #and len(peers) < int(num_of_ringos):
                print(json_obj['ttl'])
                if json_obj['ttl'] > 0 or len(json_obj['peers']) < int(num_of_ringos):
                    socketo.sendto(new_peer_data.encode('utf-8'), self.client_address)


        elif keyword == "find_rtt":
            rtt_count = json_obj['rtt_count']
            rtt_created = json_obj['created']
            if rtt_count == 1:
                rtt_count = rtt_count + 1
                new_peer_data = json.dumps({
                    'command': 'find_rtt',
                    'rtt_count': rtt_count,
                    'created': rtt_created
                })
                socketo.sendto(new_peer_data.encode('utf-8'), self.client_address)
            elif rtt_count == 2:
                # Update RTT table
                rtt_value = time.time() - json_obj['created']
                peers[str(self.client_address)] = rtt_value
                print(peers)
        else:
            print(keyword)
            print('Invalid Packet')


def discovery(server, peers, poc_name, poc_port):
    # We're sending RTT when it's the first one.
    poc_address = (poc_name, int(poc_port))
    # peers[str(poc_address)] = 0  # We don't know the RTT btw this ringo and PoC yet
    peer_data = json.dumps({
        'command': 'peer_discovery',
        'peers': peers,
        'ttl': 10,
        })
    server.socket.sendto(
        peer_data.encode('utf-8'),
        poc_address
        )

def sendrtt(server, peer_name, peer_port):
    # We're sending RTT when it's the first one.
    peer_address = (peer_name, int(peer_port))

    # peers[str(poc_address)] = 0  # We don't know the RTT btw this ringo and PoC yet
    peer_data = json.dumps({
        'command': 'find_rtt',
        'created': time.time(),
        'rtt_count': 1,
        })
    server.socket.sendto(
        peer_data.encode('utf-8'),
        peer_address
        )


def main():
    if (len(sys.argv) != 6):
        usage()

    # Interpret the argument
    # python3 ringo.py S 100.0 john 90 90
    flag = sys.argv[1]  # Getting a flag i.e) S, F, R
    local_port = sys.argv[2]  # Getting a local port i.e) 23222
    poc_name = sys.argv[3]  # Getting the port name i.e) networklab3.cc.gatech.edu
    poc_port = sys.argv[4]  # Getting the port number i.e) 8080 or 13445
    global num_of_ringos
    num_of_ringos = sys.argv[5]  # Getting the number of ringos i.e) 5

    # Define RTT Table
    # Checking if we get the right argument types
    check_flag(flag)
    check_numeric(local_port, "local-port")
    check_numeric(poc_port, "PoC-port")
    check_numeric(num_of_ringos, "N")

    # Peer Discover Here. #
    host = "127.0.0.1"
    HOST, PORT = host, int(local_port)
    server = socketserver.UDPServer((HOST, PORT), MyUDPHandler)
    server_thread = Thread(target=server.serve_forever, args=())
    server_thread.daemon = False
    server_thread.start()
    print('WELCOME TO RINGO')

    while len(peers) < int(num_of_ringos):
        # if it's not the first ringo,
        if poc_name != "0":
            # Send to PoC # Peer Discovery
            discovery(server, peers, poc_name, poc_port)
        time.sleep(1)

    print("Peer Discovery Result")
    count = 1
    for item in list(peers.keys()):
        peer_address = ast.literal_eval(item)[0]
        peer_port = ast.literal_eval(item)[1]
        # Sending RTT to every peer at this time
        sendrtt(server, peer_address, peer_port)

        print(str(count) + " - " + str(peer_address) + ":" + str(peer_port))
        count = count + 1
    print("---------------------")

    # RTT matrix
    print("RTT Table of this Ringo")
    for item in list(peers.keys()):
        # peer_address = ast.literal_eval(item)[0]
        # peer_port = ast.literal_eval(item)[1]
        sendrtt(server, peer_address, peer_port)

    # Send Packets maybe 10 times!
    while True:
        if 1 not in peers.values():
            break
        else:
            time.sleep(1)
            print(peers.values())
    # Command Line Here
    for item in list(peers.keys()):
        peer_address = ast.literal_eval(item)[0]
        peer_port = ast.literal_eval(item)[1]
        print(str(peer_address) + ":" + str(peer_port) + " - " + str(peers[item]))

    print('---------------------')

if __name__ == "__main__":
    main()
