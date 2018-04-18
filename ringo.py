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
import uuid
# import socket
import signal

PACKETS_WINDOW_SIZE = 5  # this many packets may be designated by number
SEND_BUF = 1024 # size of msg send buffer

peers = {}
rtt_matrix = {}
routes = [] # for use in findRing()

# Variables for Keep Alive
seq_ids = {}
seq_id = 0
num_active_node = 0
active_ringos = {}
global non_active
non_active = False

# Variables for file sending
pack_sequence = 0 # current sequence number
expected_packet = 0 # for use with receiving message
expected_packet_ack = 0
window = [] # packet window
file_chunks = []      # body of file to send

forwarded = False   # for use in forwarding

sendTimes = []  # the times at which packets are sent
nextAddress = ()    # the neighbor to which a message is to be forwarded

class MyUDPHandler(socketserver.BaseRequestHandler):
    def handle(self):
        data = self.request[0]
        socketo = self.request[1]
        json_obj = json.loads(data.decode("utf-8"))
        keyword = json_obj.get('command')
        peers_response = json_obj.get('peers')

        global expected_packet
        global expected_packet_ack

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
                try:
                    socketo.sendto(new_peer_data.encode('utf-8'), self.client_address)
                except:
                    pass
        elif keyword =="keepalive":
            ttl = json_obj['ttl'] - 1
            created = json_obj['created']
            seq_id = json_obj['seq_id']

            kl_data = json.dumps({
                'seq_id': seq_id,
                'command': 'keepalive',
                'created': created,
                'ttl': ttl
            })

            if ttl > 0: # received!! ttl == 1
                try:
                    socketo.sendto(kl_data.encode('utf-8'), self.client_address)
                except:
                    pass
            if ttl == 0:
                # I got this packet. the target address is alive!
                # add to sequence ids
                seq_ids.pop(seq_id, None)
        elif keyword == "find_rtt":
            rtt_count = json_obj['rtt_count']
            rtt_created = json_obj['created']
            if rtt_count == 1:
                # First Call # Arrives at the target address
                rtt_count = 2
                new_peer_data = json.dumps({
                    'command': 'find_rtt',
                    'rtt_count': rtt_count,
                    'created': rtt_created,
                })
                try:
                    socketo.sendto(new_peer_data.encode('utf-8'), self.client_address)
                except:
                    pass
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
            global rtt_matrix
            rtt_matrix[str(self.client_address)] = peers_response

            new_rtt_peer_data = json.dumps({
                'command': 'send_rtt_vector',
                'peers': peers,
                'ttl': ttl,
            })
            if ttl > 0:
                try:
                    socketo.sendto(new_rtt_peer_data.encode('utf-8'), self.client_address)
                except:
                    pass
        elif keyword == "file":
            print("received message data from " + str(self.client_address))

            data = json_obj['data'].encode('ISO-8859-1')
            incoming_seq_number = json_obj['seq_number']
            filename = json_obj['filename']
            file_length = json_obj['file_length']
            print("seq numb\t" + str(incoming_seq_number) + " and I want " + str(expected_packet))




            json_pckt = ""

            pckt_ack = json.dumps({
                    'command': 'file_ack',
                    'ack_number': incoming_seq_number,
                    'filename' : filename,
                    'file_length': file_length,
                    # 'data': data,
                    })

            if incoming_seq_number != expected_packet:
                print('Unexpected packet: ' + str(incoming_seq_number))


            if incoming_seq_number == expected_packet:  # if not expeceted, let the sender timeout
                file_chunks.append(data)

                expected_packet += 1

                # Signal to user that it is safe to input again
                if (incoming_seq_number == file_length-1):
                    print("File fully received!")
                    print(">")
                    print("flag: " + flag)

                    '''
                    Write file at receiver
                    '''
                    if flag == 'R':
                        writeToFile(filename, file_length)

                    '''
                    Forward file
                    '''
                    global forwarded
                    if flag == 'F' and forwarded == False:
                        print("I'm forwarding this file!")
                        expected_packet = 0
                        global nextAddress
                        init_window(socketo, nextAddress, filename, file_length)

            print('sending ack ' + str(incoming_seq_number) + "; still want all " + str(file_length))
            try:
                socketo.sendto(pckt_ack.encode('utf-8'), self.client_address)
            except:
                pass
        elif keyword == "file_ack": # this is an ack for the piece of the file we sent
            # data = json_obj['data']
            ack_number = json_obj['ack_number']
            filename = json_obj['filename']
            file_length = json_obj['file_length']
            print("expected ack\t" + str(expected_packet_ack))
            print("ack numb received\t" + str(ack_number))


            global pack_sequence

            if ack_number != expected_packet_ack:
                print('UNEXPECTED ACK RECEIVED')
                # send_window(socketo, self.client_address)
            else:


                global stop_event

                expected_packet_ack += 1

                print("deleting from window...")

                del window[0]
                print(str(len(window)))

                print("FILE SEQUENCE NUMBER:\t" + str(pack_sequence))
                # print("length of file_chunks:\t" + str(len(file_chunks)))

                if pack_sequence < len(file_chunks):

                    new_pckt = json.dumps({
                            'command': 'file',
                            'filename': filename,
                            'file_length':file_length,
                            'seq_number': pack_sequence,
                            'data': file_chunks[pack_sequence].decode('ISO-8859-1')
                            })
                    print('adding to window...')


                    window.append(new_pckt)
                    print(str(len(window)))


                    pack_sequence += 1

                    send_packet(socketo, self.client_address, file_length, new_pckt)

            # Signal to user that it is safe to input again
            if (ack_number == file_length-1):
                print("File fully sent!")
                print(">")
        else:
            print(keyword)
            print('Invalid Packet')

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
'''
Timeout function; loops while we still expect more acks, then resets the globals
    to receive a future file
'''
def timeout(server, client_address, file_length, timeout):
    global nextAddress
    print('TIMEOUT BEGINS HERE')
    while(True):
        global expected_packet_ack
        if (expected_packet_ack >= file_length):    # implies we've received ack for last packet
            # reset global variables
            print('breaking timer')
            global timeoutSet

            global pack_sequence
            global file_chunks

            timeoutSet = False
            file_chunks = []
            expected_packet_ack = 0
            pack_sequence = 0

            break;

        time.sleep(1)
        now = time.time()
        print("here, expected ack is " + str(expected_packet_ack) + " and file_length is " + str(file_length))
        if (expected_packet_ack < file_length and now >= sendTimes[expected_packet_ack] + timeout):
            print(expected_packet_ack)
            send_window(server, nextAddress, file_length)

'''
Used by Receiving Ringo to write the transferred file
'''
def writeToFile(filename, file_length):
    print("writing file " + str(filename))

    f = open(filename, 'wb')
    global file_chunks
    for idx in range(len(file_chunks)):
      f.write(file_chunks[idx])
    global expected_packet
    expected_packet = 0
    file_chunks = []

"""
initialize packet window
"""
def init_window(server, peer_address, filename, file_length):
    global pack_sequence

    idx = 0
    while idx < len(file_chunks) and idx < PACKETS_WINDOW_SIZE:   # stops if file_chunks is smaller than a window
        print(pack_sequence)
        new_pckt = json.dumps({
            'command': 'file',
            'filename': filename,
            'file_length': file_length, #length in packets
            'seq_number': pack_sequence,
            'data': file_chunks[idx].decode('ISO-8859-1')
            })
        window.append(new_pckt)

        pack_sequence += 1
        idx += 1

    send_window(server, peer_address, file_length)


'''
send window of packets
'''
def send_window(sock_server, client_address, file_length):
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

    try:
        socket.sendto(
            packet.encode('utf-8'),
            client_address
            )
    except:
        pass

    if (sequence < len(sendTimes)):  # check if packet was already sent
        sendTimes[sequence] = time.time()
    else:
        sendTimes.append(time.time())

    global timeoutSet
    if (json_pckt['seq_number'] == 0 and not timeoutSet):
        print("BEGINNING THREAD")
        timeoutSet = True
        Thread(target=timeout,args=(socket, client_address, file_length, 5,)).start()

def send_rtt_vector(server, peers, poc_name, poc_port):
    # We're sending RTT when it's the first one.
    poc_address = (poc_name, int(poc_port))

    peer_data = json.dumps({
        'command': 'send_rtt_vector',
        'peers': peers,
        'ttl': 6,
        })
    try:
        server.socket.sendto(
            peer_data.encode('utf-8'),
            poc_address
            )
    except:
        pass

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
    try:
        server.socket.sendto(
            peer_data.encode('utf-8'),
            peer_address
            )
    except:
        pass

def churn_tout(server, created, item, seq_id, local):

    # Timeout for each peer route A to B
    while True:
        global non_active, rtt_matrix, num_active_node
        # It's not in the sequence lists! (We got the packet back)
        if not seq_id in seq_ids:
            active_ringos[item] = 1
            # Oh just found new active ringo (Inactive to Active)
            if int(num_active_node) < len(active_ringos):
                num_active_node = len(active_ringos)
                # if non_active:!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                num_active_node = int(num_of_ringos) - 1
                non_active = False
                # peer Discovery, Find RTT, Send RTT, Find Optimal Ring
                start_peer_discovey()
                start_finding_own_rtt()
                start_finding_rtt_vectors()
                routes = []
                findRing(local, rtt_matrix, [], 0)
                break # Break timeout... Exit the Thread

        else:
            now = time.time()
            if now - created > 3:
                # Happens only few times

                # Time Out Call!
                # Remove the address from RTT Matrix
                # if rtt_matrix[item] != None:
                rtt_matrix[item] = None
                # Remove it from active ringos
                active_ringos.pop(item, None)
                # decreases current num of ringos
                non_active = True
                if int(num_active_node) > len(active_ringos):
                    num_active_node = len(active_ringos)
                    routes = []
                    findRing(local, rtt_matrix, [], 0)
                # Find Optimal Ring

                # print('found inactive node')
                break #Break the Thread
        time.sleep(1)

def churn(server, item, seq_id, local):
    while True:
        # Keep Alive works until the program termiantes
        kl_name =  ast.literal_eval(item)[0]
        kl_port =  ast.literal_eval(item)[1]
        kl_address = (kl_name, int(kl_port))
        created = time.time()
        # Generate Sequence Number
        seq_id = str(uuid.uuid4())

        # add to seq_ids list
        seq_ids[seq_id] = 1

        kl_data = json.dumps({
            'seq_id': seq_id,
            'command': 'keepalive',
            'created': created,
            'ttl': 2, # goes through one time
            })
        try:
            server.socket.sendto(
                kl_data.encode('utf-8'),
                kl_address
                )
        except:
            break

        # Make another thread
        Thread(target=churn_tout, args=(server, created, item, seq_id, local)).start()
        time.sleep(0.5)

def keep_alive(server, seq_id, local):
    # Send Packets to every node
    global kl_threads_list
    for item in list(peers.keys()):
        # For each peers, we open keep alive thread
        kl_thread = Thread(target=churn, args=(server, item, seq_id, local))
        kl_threads_list.append(kl_thread)
        kl_thread.start()

def start_peer_discovey():
    global peers, num_of_ringos, poc_name, poc_port, server
    while len(peers) < int(num_of_ringos):
        # if it's not the first ringo,
        if poc_name != "0":
            if poc_port != "0":
                # Send to PoC # Peer Discovery
                discovery(server, peers, poc_name, poc_port)


def start_printing_peer_discovery_result():
    global peers
    for item in list(peers.keys()):
        peer_address = ast.literal_eval(item)[0]
        peer_port = ast.literal_eval(item)[1]
        print(str(peer_address) + ":" + str(peer_port))

def start_finding_own_rtt():
    global peers, server
    while True:
        if 1 not in peers.values():
            break
        else:
            for item in list(peers.keys()):
                peer_address = ast.literal_eval(item)[0]
                peer_port = ast.literal_eval(item)[1]
                # Sending RTT to every peer at this time
                findrtt(server, peer_address, peer_port)

def start_finding_rtt_vectors():
    global rtt_matrix, peers, server, num_of_ringos, HOST, PORT
    rtt_matrix[str((HOST, PORT))] = peers
    while True:
        for item in list(peers.keys()):
            peer_address = ast.literal_eval(item)[0]
            peer_port = ast.literal_eval(item)[1]
            send_rtt_vector(server, peers, peer_address, peer_port)
        if len(rtt_matrix) == int(num_of_ringos):
            break;

def findRing(node, cities, path, distance):
    # Add way point
    path.append(node)

    # Delete None value cities
    new_cities = cities.copy()
    new_cities2 = cities.copy()
    for key in new_cities:
        if new_cities[key] == None:
            new_cities2.pop(key, None)
    cities = new_cities2

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
    global offline, kl_threads_list, rtt_matrix, flag, poc_name, local, poc_port, num_of_ringos, current_num_of_ringos, seq_id, active_ringos, num_active_node, HOST, PORT, server, routes
    flag = sys.argv[1]  # Getting a flag i.e) S, F, R
    local_port = sys.argv[2]  # Getting a local port i.e) 23222
    poc_name = sys.argv[3]  # Getting the port name i.e) networklab3.cc.gatech.edu
    poc_port = sys.argv[4]  # Getting the port number i.e) 8080 or 13445
    num_of_ringos = sys.argv[5]  # Getting the number of ringos i.e) 5
    current_num_of_ringos = num_of_ringos
    check_flag(flag)
    check_numeric(local_port, "local-port")
    check_numeric(poc_port, "PoC-port")
    check_numeric(num_of_ringos, "N")
    kl_threads_list = []

    offline = False

    # global non_active
    # non_active = False
    num_active_node = int(num_of_ringos)
    # Peer Discover Here. #

    # , int(local_port)
    HOST, PORT = socket.gethostbyname(socket.gethostname()), int(local_port)

    server = socketserver.UDPServer((HOST, PORT), MyUDPHandler)
    server_thread = Thread(target=server.serve_forever, args=())
    server_thread.daemon = False
    server_thread.start()

    print('WELCOME TO RINGO')
    # Peer Discovery Start
    start_peer_discovey()

    # Printing Peer Discoery Result
    print("Peer Discovery Result")
    start_printing_peer_discovery_result()
    time.sleep(1)

    # Find RTT # Peer Discovery Here
    start_finding_own_rtt()
    time.sleep(1)

    # Find RTT Vectors
    print("Finding Distance Vector of this Ringo...")
    # Adding our distance vector to our RTT matrix
    start_finding_rtt_vectors()
    print("Finishing Finding RTT Matrix..")

    # Find Ring
    local = str((HOST,PORT))
    routes = []
    findRing(local, rtt_matrix, [], 0)
    routes.sort()

    keep_alive(server, seq_id, local)

    if len(routes) == 0:
        print ("FAILED TO FIND OPTIMAL RING")

    # Command Line User Interface Start here
    print ("\n")
    print("My address:\t" + str(routes[0][1][0]))   #this will always be the current ringo
    print("Next address:\t" + str(routes[0][1][1])) #next ringo in optimal ring

    # nextName = routes[0][1][1].split(",")[0][2:-1]  # trim of parenths
    # nextPort = int(routes[0][1][1].split(",")[1][:5])
    # global nextAddress
    # nextAddress = (nextName, nextPort)  # this is the next address
    # nextAddress = ('127.0.0.1',6000)

    while True:
        nextName = routes[0][1][1].split(",")[0][2:-1]  # trim of parenths
        nextPort = int(routes[0][1][1].split(",")[1][:5])
        global nextAddress
        nextAddress = (nextName, nextPort)

        print('Enter Commands (show-matrix, show-ring, offline [seconds], send [filename.type], or disconnect)')
        text = input('> ')

        if text == 'show-matrix':
            print(json.dumps(rtt_matrix, indent=2, sort_keys=True))
            # print(rtt_matrix)
            print ("\n")
        elif text == 'peers':
            print(peers)
            # print(rtt_matrix)
            print ("\n")

        elif text == 'show-ring':
            routes = []
            findRing(local, rtt_matrix, [], 0)
            routes.sort()
            print('The Total Cost: '+str(routes[0][0]))
            print('The Optimal Ring path: '+str(routes[0][1]))
            print("\n")

        elif text == 'disconnect':
            print('Good bye! (Killing Threads. You will be directed to terminal)')
            print ("\n")
            # for kl_thread in kl_threads_list:
            #     # kl_thread.join()
            #     # kl_thread.daemon = True
            # server_thread.join()
            server.get_request()
            server.server_close()
            server.shutdown()
            # signal.signal(signal.SIGINT, signal.SIG_DFL)
            # server.accept()
            sys.exit(0)
            break
        elif text.startswith("offline") :
            if text.split()[0] == 'offline':
                try:
                    duration = text.split()[1]
                    server.get_request()
                    server.server_close()
                    server.shutdown()
                    print('server is offline; Will be back in '+duration+' seconds.')
                    time.sleep(int(duration))
                    print('Now server is online')
                    offline = True
                    break;
                except:
                    print('Bac Command')
        elif text.startswith("send"):
            if text.split()[0] == 'send':
                if (flag != 'S'):
                    print('Illegal Request!')
                    print('Only Senders may make send requests')
                else:
                    print("FILENAME:\t" + text.split()[1])
                    file_name = text.split()[1]
                    f = open(file_name, "rb")
                    data = f.read()

                    file = []

                    idx = 0
                    while (idx + SEND_BUF) < len(data):
                        file.append(data[idx:idx+SEND_BUF])
                        idx += SEND_BUF
                    file.append(data[idx:])

                    f.close()

                    global expected_packet_ack
                    global pack_sequence
                    global file_chunks

                    # iniitialize variables for file the sending
                    file_chunks = file
                    file_length = len(file_chunks)
                    expected_packet_ack = 0
                    pack_sequence = 0

                    init_window(server.socket, nextAddress, file_name, file_length)
        else:
            print('Bad Command\n')
    if offline:
        main()
if __name__ == "__main__":
    main()
