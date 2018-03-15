# RDT Ringo
#
# a Ringo node using the Reliable Data Transfer protocol, using skeletal code based on
# socket_echo_server_dgram.py and socket_echo_client_dgram.py from https://pymotw.com/3/socket/udp.html
#
# random string generator borrowed from 
# https://stackoverflow.com/questions/2257441/random-string-generation-with-upper-case-letters-and-digits-in-python
#
# each ringo acts as client and server; must find local and foreign addresses, bind local address to port

import socket
import sys

import time
import random
import string

import _thread
import threading


def usage():
    print ("Usage: \n\tpython ringo.py <flag> <local-port> <PoC-name> <PoC-port> <N> ");
    sys.exit(1)

def check_flag(flag):
    if (flag=="S"):
        return "S"
    elif (flag=="F"):
        return "F"
    elif (flag=="R"):
        return "R"
    else:
        usage();

def check_numeric(arg, param):
    val = ""
    try:
   	    val = int(arg)
    except ValueError:
	    print(param + " must be an int")
	    sys.exit(1)
    return val


### RTT FUNCTIONS ###
#
# determineTimeSending - sends messages to PoC and times response; message sent is a randomly-generated 32-character
#                        string; checks response for matching string, adds time to respond to total time; after a loop of 
#                        ten, prints average
#
# determineTimeReceiving - receives messages from ringo for whom this ringo is PoC; sends back message as acknowledgement
#                         

def determineTimeSending(poc_addr, sock): # determine time for ringo's dv
    avgTime = 0.0;
    i = 0;
    while (i < 10):
        try:
            initTime = time.monotonic();
            message = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(32)).encode()

            # Send data
            print('sending time message{!r}'.format(message))
            sent = sock.sendto(message, poc_addr)

            # Receive response
            print('waiting to receive');
            data, server = sock.recvfrom(4096);
            print('received {!r}'.format(data));

            if (data == message):   # respond only to replies to messages sent
                roundTripTime = time.monotonic() - initTime;  
                avgTime += float(roundTripTime);
        finally:
            i += 1;

    avgTime /= 10;
    print("average time:\t" + str(avgTime));
    # sock.close();

def determineTimeReceiving(sock):   # help adjacent ringo determine time for its dv
    while True:

        print('\nwaiting to receive message')
        data, address = sock.recvfrom(4096)

        print('received {} bytes from {}'.format(
            len(data), address))

        if data:
            print("data:\t" + str(data))

            sent = sock.sendto(data, address)
            print('sent {} bytes back to {}'.format(
                sent, address))


def main():

    # tm = time.monotonic();
    # print(tm);
    # tm -= 3;
    # print(tm);
    # strtm = str(tm);
    # print(strtm);
    # sys.exit(1);

    # print(sys.version);
    

    # sys.exit(1);

    if (len(sys.argv) != 6):
        usage();

    role = check_flag(sys.argv[1]);    # job of ringo (sender, receiver, forwarder)

    l_port = check_numeric(sys.argv[2], "local-port");    # local port number

    poc_port = check_numeric(sys.argv[4], "PoC-port");    # poc port 

    n_size = check_numeric(sys.argv[5], "N"); # size of network

    # create UDP sockets for listening, sending (respectively)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM);
    # poc_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM);


    # define part addresses
    # 'localhosts' should be changed before testing on network
    local_addr = ('localhost', l_port);
    poc_addr = ('localhost', poc_port);
    print('starting up on {} port {}'.format(*local_addr));
    print('starting up on {} port {}'.format(*poc_addr));    


    # bind the sockets to the ports
    sock.bind(local_addr);
    # poc_sock.bind(poc_addr);




    ### Seems like threads should be used to listen and speak to ports for message, listen and speak to ports for "keep-alives",
    ### and listen for commands;

    try:
        t1 = threading.Thread(target=determineTimeSending, args=(poc_addr, sock));
        t1.start();
        # t1.join(timeout = 5);
        _thread.start_new_thread(determineTimeReceiving, (sock));

    except:
        print ("Error: unable to start thread")

    while(1):
        pass


    # if (role is "S"):
    #     _thread.start_new_thread(determineTimeSending(poc_addr, sock));

    # elif (role is "F"):
    #     msgForward();

    # elif (role is "R"):
    #     _thread.start_new_thread(determineTimeReceiving(sock));


    


    print( "Made it this far...");

# Create a UDP socket
# sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# # Bind the socket to the port
# server_address = ('localhost', 10000)
# print('starting up on {} port {}'.format(*server_address))
# sock.bind(server_address)

# while True:
#     print('\nwaiting to receive message')
#     data, address = sock.recvfrom(4096)

#     print('received {} bytes from {}'.format(
#         len(data), address))
#     print(data)

#     if data:
#         sent = sock.sendto(data, address)
#         print('sent {} bytes back to {}'.format(
#             sent, address))

if __name__ == "__main__":
    main();
