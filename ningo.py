# RDT Ringo
#
# a Ringo node using the Reliable Data Transfer protocol, using skeletal code based on
# socket_echo_server_dgram.py and socket_echo_client_dgram.py from https://pymotw.com/3/socket/udp.html
#
# bestRing() is a slightly modified version of the function of a brute-force solution created by Simon Westphahl <westphahl@gmail.com>;
# modifications made include renaming and converting to python3
#

import socket
import socketserver
import sys
from threading import Thread
from datetime import datetime
import time
import json
import timeit
import ast
import socket

# Supporting addition, subtraction, multiplication and division.
peers = {}
rtt_matrix = {}
routes = [] # for use in findRing()


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
            ttl = json_obj['ttl'] - 1

            for key in peers_response:
                peers[key] = 1
            new_peer_data = json.dumps({
                'command': 'peer_discovery',
                'peers': peers,
                'ttl': ttl
            })
            # num_of_ringos = sys.argv[5]
            if ttl > 0:
                socketo.sendto(new_peer_data.encode('utf-8'), self.client_address)
        elif keyword == "find_rtt":
            rtt_count = json_obj['rtt_count']
            rtt_created = json_obj['created']
            if rtt_count == 1:
                rtt_count = 2
                new_peer_data = json.dumps({
                    'command': 'find_rtt',
                    'rtt_count': rtt_count,
                    'created': rtt_created,
                })
                socketo.sendto(new_peer_data.encode('utf-8'), self.client_address)
            elif rtt_count == 2:
                # Update RTT table
                rtt_value = time.time() - json_obj['created']
                if peers.get(str(self.client_address)):
                    peers[str(self.client_address)] = rtt_value
                # print(peers)
                print('Received!')
            else:
                print('This should not happen')
        elif keyword =="send_rtt_vector":
            # Receive a distance vector
            peers_response = json_obj['peers']
            ttl = json_obj['ttl'] - 1

            rtt_matrix[str(self.client_address)] = peers_response

            new_rtt_peer_data = json.dumps({
                'command': 'send_rtt_vector',
                'peers': peers,
                'ttl': ttl
            })
            if ttl > 0:
                socketo.sendto(new_rtt_peer_data.encode('utf-8'), self.client_address)
        else:
            print(keyword)
            print('Invalid Packet')


def send_rtt_vector(server, peers, poc_name, poc_port):
    # We're sending RTT when it's the first one.
    poc_address = (poc_name, int(poc_port))
    # peers[str(poc_address)] = 0  # We don't know the RTT btw this ringo and PoC yet
    peer_data = json.dumps({
        'command': 'send_rtt_vector',
        'peers': peers,
        'ttl': 6,
        })

    server.socket.sendto(
        peer_data.encode('utf-8'),
        poc_address
        )

def discovery(server, peers, poc_name, poc_port):
    # We're sending RTT when it's the first one.
    poc_address = (poc_name, int(poc_port))
    # peers[str(poc_address)] = 0  # We don't know the RTT btw this ringo and PoC yet
    peer_data = json.dumps({
        'command': 'peer_discovery',
        'peers': peers,
        'ttl': 6,
        })

    server.socket.sendto(
        peer_data.encode('utf-8'),
        poc_address
        )

def findrtt(server, peer_name, peer_port):
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



def findRing(node, cities, path, distance):
    # Add way point
    print(node,cities,path,distance)
    path.append(node)

    # Calculate path length from current to last node
    if len(path) > 1:
        distance += cities[path[-2]][node]

    # If path contains all cities and is not a dead end,
    # add path from last to first city and return.
    if (len(cities) == len(path)) and (path[0] in cities[path[-1]]):
        global routes
        path.append(path[0])
        distance += cities[path[-2]][path[0]]
        print (path, distance)
        routes.append([distance, path])
        return

    # Fork paths for all possible cities not yet used
    for city in cities:
        if (city not in path) and (node in cities[city]):
            findRing(city, dict(cities), list(path), distance)

def main():

    if (len(sys.argv) != 6):
        usage()

    print('Host name: '+ str(socket.gethostbyname(socket.gethostname())))

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
    # host = "127.0.0.1"
    host = socket.gethostbyname(socket.gethostname())
    HOST, PORT = host, int(local_port)
    server = socketserver.UDPServer((HOST, PORT), MyUDPHandler)
    server_thread = Thread(target=server.serve_forever, args=())
    server_thread.daemon = False
    server_thread.start()
    print('WELCOME TO RINGO')

    while len(peers) < int(num_of_ringos):
        # if it's not the first ringo,
        if poc_name != "0":
            if poc_port != "0":
                # Send to PoC # Peer Discovery
                discovery(server, peers, poc_name, poc_port)

    print("Peer Discovery Result")
    for item in list(peers.keys()):
        peer_address = ast.literal_eval(item)[0]
        peer_port = ast.literal_eval(item)[1]
        print(str(peer_address) + ":" + str(peer_port))

    time.sleep(2)
    # Find RTT.
    while True:
        if 1 not in peers.values():
            print(peers.values())
            print('Just printed Distance Vector')
            break
        else:
            for item in list(peers.keys()):
                peer_address = ast.literal_eval(item)[0]
                peer_port = ast.literal_eval(item)[1]
                # Sending RTT to every peer at this time
                findrtt(server, peer_address, peer_port)
            time.sleep(1)

    print("-------Printing Distance Vector of this Ringo--------")
    # Adding our distance vector to our RTT matrix
    rtt_matrix[str((HOST, PORT))] = peers

    print("RTT Table of this Ringo")

    while True:
        for item in list(peers.keys()):
            peer_address = ast.literal_eval(item)[0]
            peer_port = ast.literal_eval(item)[1]
            send_rtt_vector(server, peers, peer_address, peer_port)
        if len(rtt_matrix) == int(num_of_ringos):
            print("done!")
            break;

    print(rtt_matrix)
    print('----END OF RTT Table')

    print ("Start: " + str((HOST, PORT)))

    # matrixKeys = 
    local = str((HOST,PORT))
    findRing(local, rtt_matrix, [], 0)
    print ("\n")
    routes.sort()
    if len(routes) != 0:
        print ("Shortest route: %s" % routes[0])
    else:
        print ("FAILED TO FIND OPTIMAL RING")

    # Command Line Here
    print("----")
    print('(enter commands)')

    while True:
        text = input('') 

        if (text == 'show-matrix'):
            print(rtt_matrix)
            print('')

        if (text == 'show-ring'):
            print(routes[0])
            print('')

        if (text == 'disconnect'):
            print('Goody-bye!')
            print('')
            sys.exit(1)



    # for item in list(peers.keys()):
    #     peer_address = ast.literal_eval(item)[0]
    #     peer_port = ast.literal_eval(item)[1]
    #     print(str(peer_address) + ":" + str(peer_port) + " - " + str(peers[item]))

    
    

if __name__ == "__main__":
    main()
