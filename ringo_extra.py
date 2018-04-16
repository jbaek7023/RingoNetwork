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
from threading import Thread, Event
from datetime import datetime
import time
import json
import timeit
import ast
# import socket


PACKETS_WINDOW_SIZE = 5  # this many packets may be designated by number
SEND_BUF = 1024 # size of msg send buffer

peers = {}
rtt_matrix = {}
routes = [] # for use in findRing()

pack_sequence = 0 # current sequence number
expected_packet = 0 # for use with receiving message
expected_packet_ack = 0
window = [] # packet window
file_text = []      # body of file to send

forwarded = False   # for use in forwarding

sendTimes = []  # the times at which packets are sent
nextAddress = ()    # the neighbor to which a message is to be forwarded

stop_event = Event();


def usage():
    print ("Usage: python3 ringo.py <flag> <local-port> <PoC-name> <PoC-port> <N>")
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


timeoutSet = False
def timeout(server, client_address, filelength, timeout):
    
    while(True):
        if stop_event.is_set():
            global expected_packet_ack
            expected_packet_ack = 0
            global pack_sequence
            pack_sequence = 0
            global file_length
            file_length = 0;
            break;
        time.sleep(1)
        now = time.time()
        print("here, expected ack is " + str(expected_packet_ack) + " and file_length is " + str(filelength))
        if (expected_packet_ack < filelength and now >= sendTimes[expected_packet_ack] + timeout):
            print(expected_packet_ack)
            send_window(server, client_address, filelength)

def writeToFile(filename, file_data, file_length):
    print("writing file " + str(filename))

    f = open(filename, 'wb')
    
    for idx in range(file_length):
      f.write(file_data[idx])
   

def writeToTextFile(filename, file_data, file_length):
    print("writing file " + str(filename))

    f = open(filename, 'w')
    for idx in range(file_length):
      f.write(file_text[idx])
    # file_text = []  # clear file_text for future use
    # print('file_text is now:\t')
    # print(file_text)



class MyUDPHandler(socketserver.BaseRequestHandler):
    def handle(self):
        data = self.request[0]
        socketo = self.request[1]
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

        elif keyword == "file":
            print("received message data from " + str(self.client_address))

            incoming_seq_number = json_obj['seq_number']
            filename = json_obj['filename']
            file_length = json_obj['file_length']
            
            if (filename[-4:] == '.txt'):   # text files are special
                data = json_obj['data']
            
            if (filename[-4:] != '.txt'):   # text files are special
                data = json_obj['data'].encode('ISO-8859-1')
            
            print("seq numb\t" + str(incoming_seq_number))


            global expected_packet

            json_pckt = ""

            pckt_ack = json.dumps({
                    'command': 'file_ack',
                    'ack_number': incoming_seq_number,
                    'filename' : filename,
                    'file_length': file_length,
                    # 'data': data,
                    })

            if incoming_seq_number == expected_packet:
                file_text.append(data)

                expected_packet += 1

            socketo.sendto(pckt_ack.encode('utf-8'), self.client_address)

            # Signal to user that it is safe to input again
            if (incoming_seq_number == file_length-1):
                print("File fully received!")
                print(">")
                print("flag: " + flag)

                '''
                Write file at receiver
                '''
                file_data = file_text
                if flag == 'R':
                    if (filename[-4:] == '.txt'):
                        writeToTextFile(filename, file_data, file_length)
                    else:
                        writeToFile(filename, file_data, file_length)
                     # clear file_text for future use 
                    global expected_packet
                    expected_packet = 0

                '''
                Forward file
                '''
                global forwarded
                if flag == 'F' and forwarded == False:
                    print("I'm forwarding this file!")
                    global nextAddress
                    init_window(socketo, nextAddress, filename, file_length)

        elif keyword == "file_ack":
            # data = json_obj['data']
            ack_number = json_obj['ack_number']
            filename = json_obj['filename']
            file_length = json_obj['file_length']
            print("expected ack\t" + str(expected_packet_ack))
            print("ack numb received\t" + str(ack_number))

            
            global pack_sequence

            if ack_number != expected_packet_ack:
                print('UNEXPECTED ACK RECEIVED')
            else:

                global expected_packet_ack

                expected_packet_ack += 1

                print("deleting from window...")

                del window[0]
                print(str(len(window)))

                print("FILE SEQUENCE NUMBER:\t" + str(pack_sequence))

                # Signal to user that it is safe to input again
                if (ack_number == file_length-1):
                    print("File fully sent!")
                    print(">")
                    global stop_event
                    stop_event.set()
                    # global timeoutSet
                    # timeoutSet = False
                    # expected_packet_ack = 0
                    # global pack_sequence
                    # pack_sequence = 0
                    # global file_length
                    # file_length = 0;

                    
                    # global file_text
                    # file_text = []


                else :
                    if pack_sequence < len(file_text):

                        if (filename[-4:] == '.txt'):   # text files are special
                            data = file_text[pack_sequence]

                        if (filename[-4:] != '.txt'):   # text files are special
                            data = file_text[pack_sequence].decode('ISO-8859-1')

                        new_pckt = json.dumps({
                                'command': 'file',
                                'filename': filename,
                                'file_length':file_length,
                                'seq_number': pack_sequence,
                                'data': data
                                })
                        print('adding to window...')                


                        window.append(new_pckt)
                        print(str(len(window)))


                        pack_sequence += 1

                        send_packet(socketo, self.client_address, file_length, new_pckt)


        else:
            print(keyword)
            print('Invalid Packet')


"""
initialize packet window
"""
def init_window(server, client_address, filename, file_length):
    print("I want to send your message!")


    global pack_sequence

    idx = 0
    
    while idx < len(file_text) and idx < PACKETS_WINDOW_SIZE:   # stops if file_text is smaller than a window
        print(pack_sequence)
        
        if (filename[-4:] == '.txt'):
            data = file_text[idx]

        if (filename[-4:] != '.txt'):   # text files are special
            # print('this is still a text file')
            data = file_text[idx].decode('ISO-8859-1')

        new_pckt = json.dumps({
            'command': 'file',
            'filename': filename,
            'file_length': file_length, #length in packets
            'seq_number': pack_sequence,
            'data': data
            })
        window.append(new_pckt)

        pack_sequence += 1
        idx += 1

    global stop_event
    if not stop_event.is_set():
        stop_event.set()
        Thread(target=timeout,args=(socket, client_address, file_length, 5,)).start()

    send_window(server, client_address, file_length)


'''
send window of packets
'''
def send_window(sock_server, client_address, file_length):
    print("I'm going to send your packets!")

    for packet in window:
        
        send_packet(sock_server, client_address, file_length, packet)

'''
Send packet data
'''
def send_packet(socket, client_address, file_length, packet):
    json_pckt = json.loads(packet) # stringify for printing
    sequence = json_pckt['seq_number']
    print("sending packet\t" + str(json_pckt['seq_number']))
    print("sending to " + str(client_address))

    socket.sendto(
        packet.encode('utf-8'),
        client_address
        )

    if (sequence < len(sendTimes)):  # check if packet was already sent
        sendTimes[sequence] = time.time()
    else:
        sendTimes.append(time.time())
    


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
        routes.append([distance, path])
        return

    # Fork paths for all possible cities not yet used
    for city in cities:
        if (city not in path) and (node in cities[city]):
            findRing(city, dict(cities), list(path), distance)



def main():

    if (len(sys.argv) != 6):
        usage()

    global flag
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
    HOST = "127.0.0.1"
    # host = socket.gethostbyname(socket.gethostname())
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

    time.sleep(1)

    # Find RTT.
    while True:
        if 1 not in peers.values():
            break
        else:
            for item in list(peers.keys()):
                peer_address = ast.literal_eval(item)[0]
                peer_port = ast.literal_eval(item)[1]
                # Sending RTT to every peer at this time
                findrtt(server, peer_address, peer_port)
    time.sleep(1)
    print("Finding Distance Vector of this Ringo...")
    # Adding our distance vector to our RTT matrix
    rtt_matrix[str((HOST, PORT))] = peers
    while True:
        for item in list(peers.keys()):
            peer_address = ast.literal_eval(item)[0]
            peer_port = ast.literal_eval(item)[1]
            send_rtt_vector(server, peers, peer_address, peer_port)
        if len(rtt_matrix) == int(num_of_ringos):
            print("Finishing Finding RTT Matrix..")
            break;

    # matrixKeys =
    local = str((HOST,PORT))
    findRing(local, rtt_matrix, [], 0)
    routes.sort()

    if len(routes) == 0:
        print ("FAILED TO FIND OPTIMAL RING")

    # Command Line User Interface Start here
    print ("\n")

    print("My address:\t" + str(routes[0][1][0]))   #this will always be the current ringo
    print("Next address:\t" + str(routes[0][1][1])) #next ringo in optimal ring
    
    nextName = routes[0][1][1].split(",")[0][2:-1]  # trim of parenths
    nextPort = int(routes[0][1][1].split(",")[1][:5])
    global nextAddress
    nextAddress = (nextName, nextPort)  # this is the next address 
    # nextAddress = ('127.0.0.1',6000)

    while True:
        print('Enter Commands (show-matrix, show-ring or disconnect)')
        text = input('> ')

        if text == 'show-matrix':
            print(json.dumps(rtt_matrix, indent=2, sort_keys=True))
            # print(rtt_matrix)
            print ("\n")

        if text == 'show-ring':
            print('The Total Cost: '+str(routes[0][0]))
            print('The Optimal Ring path: '+str(routes[0][1]))
            print("\n")

        if text == 'disconnect':
            print('Goody-bye!')
            print ("\n")
            # server_thread.join()
            server.server_close()
            server.shutdown()
            sys.exit(1)

        if text.split()[0] == 'send':
            if (flag != 'S'):
                print('Illegal Request!')
                print('Only Senders may make send requests')
            else:
                print("FILENAME:\t" + text.split()[1])
                file_name = text.split()[1]

                if file_name[-4:] == '.txt':    # text files are special
                    print('this is a text file')
                    f = open(file_name, "r")
                else:
                    f = open(file_name, "rb")
                data = f.read()

                idx = 0
                
                file = []
                while (idx + SEND_BUF) < len(data):
                    file.append(data[idx:idx+SEND_BUF])
                    idx += SEND_BUF
                file.append(data[idx:])

                global file_text
                file_text = file
                
                file_length = len(file_text)

                print (file_length)


                f.close()

                init_window(server.socket, nextAddress, file_name, file_length)


if __name__ == "__main__":
    main()



