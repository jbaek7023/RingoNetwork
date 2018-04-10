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

'''
TODO:
use window size on stop_events
'''

PACKETS_WINDOW_SIZE = 5  # this many packets may be designated by number
# GO_BACK_N = PACKETS_WINDOW_SIZE / 2 # this many packets may remain unacknowledged
SEND_BUF = 1024 # size of msg send buffer

peers = {}
rtt_matrix = {}
routes = [] # for use in findRing()

pack_sequence = 0 # current sequence number
expected_packet = 0 # for use with receiving message
expected_packet_ack = 0
proceed = True # for use with GBN protocol
window = [] # packet window
# base = 0    # base of packet window
file_text = []      # body of file to send
fileLength = 0       # length of file in packets
forwarded = False   # for use in forwarding


been_tested1 = False # for testing unexpected acks
been_tested2 = False

# stop_event = Event()    # Event object used to send signals from one thread to another
threads = []    # list of threads used for timeouts\
# stop_events = []

timers = [] # timers used to measure packet timeouts

ack_received = False
# stop_event = Event()

# cliAddr = ""    # this will be integrated into global "manager"
stop_events = [] 

# populate stop_events with 5 different events
for i in range(PACKETS_WINDOW_SIZE):
    stop_events.append(Event())


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

# def timeout(socketo, client_address, seq_number, new_pckt, timeout):
#     i = 0
#     while i < timeout:
#         time.sleep(1)
#         i += 1
#     if (expected_packet_ack == seq_number):
#         print("TIMEOUT:\tPACKET " + str(seq_number))

# ack_received = False
def timeout(server, client_address, packet_number, timeout):
    i = 0
    # global ack_received
    while i < timeout * 100:
        if stop_events[packet_number % 5].is_set():
            print("stop event " + str(packet_number % 5) + " was set")
            break
        time.sleep(.01)
        i += 1
    if i >= (timeout*100):
        print("TIMEOUT ON "+str(packet_number))
        # print(json.loads(window[expected_packet_ack])['seq_number'])
        if packet_number == expected_packet_ack or packet_number == expected_packet_ack + PACKETS_WINDOW_SIZE-1:
            # resend window if lost first packet or if timed out on packet before it was expected 
            # that's a thing that can happen because python is weird
            print("PACKET " + str(packet_number) +" RESENDS WINDOW")
            send_window(server, client_address)
    # ack_received = False

def writeToFile(filename, number, data):
    print("writing from " + str(number))
    if number == 0:
        f = open(filename, 'w')
    else:
        f = open(filename, 'a')
    f.write(data)



# class Timer:
#     # should we include a counter, so it gives up after COUNTER tries?
#     # I think not, it should keep trying as long as peer is thought to be alive

#     def __init__(self, socket, peer_address, packet):
#         self.thread = Thread(target=self.run)
#         self.socket = socket
#         self.peer_address = peer_address
#         self.packet = packet
        
#     def run(self):
#         i = 0

#         # "timeout" after 5 seconds
#         while i < 5:
#             i += 1
#             time.sleep(1)

#         packet_number = json.loads(self.packet)['seq_number']
#         if packet_number == expected_packet_ack: # still waiting for ack?
#             self.socket.sendto(self.packet, self.peer_address)
#             self.run()


# Example of Timer() usage
'''
timer = Timer()
timer.run()
print("well that just happened")
timer.run()
'''


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
        # filename = json_obj.get('filename')

        # print(self)
        # print()
        # print(socketo)

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

            data = json_obj['data']
            incoming_seq_number = json_obj['seq_number']
            filename = json_obj['filename']
            file_length = json_obj['file_length']
            print("seq numb\t" + str(incoming_seq_number))

            # f = open('newText.txt', 'a')

            global expected_packet
            global been_tested1
            global been_tested2

            json_pckt = ""

            if incoming_seq_number == 6 and been_tested1 == False:
                # pckt_ack = json.dumps({
                #         'command': 'file_ack',
                #         'ack_number': 3,
                #         'filename' : filename,
                #         'data': data
                #         })
                # been_tested1 = True

                # DO NOTHING; TESTING TIME OUT ON WITH NO ACK
                been_tested1 = True

            
            elif incoming_seq_number == 23 and been_tested2 == False:
                pckt_ack = json.dumps({
                        'command': 'file_ack',
                        'ack_number': 3,
                        'filename' : filename,
                        'file_length': file_length,
                        'data': data
                        })
                been_tested2 = True
            else:
                pckt_ack = json.dumps({
                        'command': 'file_ack',
                        'ack_number': incoming_seq_number,
                        'filename' : filename,
                        'file_length': file_length,
                        'data': data,
                        })

                if incoming_seq_number == expected_packet:
                    # f.write(data)
                    writeToFile(filename, incoming_seq_number, data)

                    expected_packet += 1

            socketo.sendto(pckt_ack.encode('utf-8'), self.client_address)

            '''
            THIS IS WHERE FILE FORWARDING WOULD TAKE PLACE
            '''
            # print("FILE_LENGTH: "+str(file_length))

            # Signal to user that it is safe to input again
            if (incoming_seq_number == file_length-1):
                print("File fully received!")
                print(">")

                '''
                Forward packet
                '''
                # global fileLength
                # global forwarded
                # # find next peer in ring
                # if (ack_number == fileLength) and (flag == 'F') and (forwarded == 'False'):
                #     init_window(socketo, peer_address, filename, fileLength)

        elif keyword == "file_ack":
            data = json_obj['data']
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

                global expected_packet_ack
                global stop_event
                # global ack_received
                # ack_received = True
                stop_events[ack_number % 5].set()
                if stop_events[ack_number % 5].is_set():
                    print("stop event set")

                expected_packet_ack += 1

                print("deleting from window...")

                del window[0]
                print(str(len(window)))

                print("FILE SEQUENCE NUMBER:\t" + str(pack_sequence))
                # print("length of file_text:\t" + str(len(file_text)))

                if pack_sequence < len(file_text):
                    
                    new_pckt = json.dumps({
                            'command': 'file',
                            'filename': filename,
                            'file_length':file_length,
                            'seq_number': pack_sequence,
                            'data': file_text[pack_sequence]
                            })
                    print('adding to window...')                

                    # ack_received = False
                    # stop_event = Event()

                    # if appending new stop events...
                    # stop_events.append(Event())

                    # if stop_events length is set...
                    stop_events[pack_sequence % 5].clear()

                    window.append(new_pckt)
                    print(str(len(window)))

                    Thread(target=timeout, args=(socketo, self.client_address, pack_sequence, 5,)).start()

                    


                    pack_sequence += 1

                    send_packet(socketo, self.client_address, new_pckt)

                    # Signal to user that it is safe to input again
                    if (pack_sequence == file_length-1):
                        print("File fully sent!")
                        print(">")

                    # socketo.sendto(
                    #     new_pckt.encode('utf-8'),
                    #     self.client_address
                    #     )

                    '''
                    Set timeout for new packet
                    '''
                    # threads.append(Thread(target=timeout, args=(socketo, self.client_address, pack_sequence, new_pckt, 5,)))
                    # stop_events.append(Event())
                    # threads[-1].start()
                    # threads[-1].join(timeout=5)
                    # stop_events[-1].set()



                    # timers.append(Timer(socketo, self.client_address, new_pckt))
                    # timers[-1].run()



        else:
            print(keyword)
            print('Invalid Packet')


"""
initialize packet window
"""
def init_window(server, peer_address, filename, file_length):
    print("I want to send your message!")


    global pack_sequence

    idx = 0
    while idx < len(file_text) and idx < PACKETS_WINDOW_SIZE:   # stops if file_text is smaller than a window
        print(pack_sequence)
        new_pckt = json.dumps({
            'command': 'file',
            'filename': filename,
            'file_length': file_length, #length in packets
            'seq_number': pack_sequence,
            'data': file_text[expected_packet_ack+idx]
            })
        window.append(new_pckt)

        # threads.append(Thread(target=timeout, args=(server, poc_address, pack_sequence, new_pckt, 5,)))
        # stop_events.append(Event())

        # timers.append(Timer(server, poc_address, new_pckt))

        pack_sequence += 1
        idx += 1

    # send_first_window(server, poc_address)
    send_window(server, peer_address)


'''
send window of packets
'''
def send_window(sock_server, client_address):
    print("I'm going to send your packets!")

    # print(sock_server)

    # print(server_name)

    # print(len(window))
    # poc_address = (poc_name, int(poc_port)) 
    for packet in window:
        # json_pckt = json.loads(packet) # stringify for printing
        # print("sending packet\t" + str(json_pckt['seq_number']))
        # sock_server.sendto(
        #     packet.encode('utf-8'),
        #     client_address
        #     )
        send_packet(sock_server, client_address, packet)

        '''
        initialize timeouts
        '''
        # seq_number = json_pckt['seq_number']   
        
        # threads[seq_number].start()
        # threads[seq_number].join(timeout=5)
        # stop_events[seq_number].set()
        
        # Thread(target=timeout,args=(sock_server, client_address, seq_number, packet, 5,)).start()

        # timers[idx].run()

def send_packet(socket, client_address, packet):
    json_pckt = json.loads(packet) # stringify for printing
    print("sending packet\t" + str(json_pckt['seq_number']))
    socket.sendto(
        packet.encode('utf-8'),
        client_address
        )
    # stop_events.append(Event())
    stop_events[json_pckt['seq_number'] % 5].clear()


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

    # print('Host name: '+ str(socket.gethostbyname('google.com')))
    #
    # sys.exit(1)
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

    # very hacky way to write data to file: open here, append later
    # if flag == "R":
    #     f = open('newText.txt', 'w')

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
                f = open(file_name, 'r')
                data = f.read()

                idx = 0
                while (idx + SEND_BUF) < len(data):
                    file_text.append(data[idx:idx+SEND_BUF])
                    idx += SEND_BUF
                file_text.append(data[idx:])
                # print("INIT LENGTH OF FILE_TEXT:\t" + str(len(file_text)))
                file_length = len(file_text)

                f.close()
                # print(len(file_text))
                # sys.exit(1)
                destination = (poc_name, int(poc_port))

                init_window(server.socket, destination, file_name, file_length)


if __name__ == "__main__":
    main()



