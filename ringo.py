# RDT Ringo
#
# a Ringo node using the Reliable Data Transfer protocol, using skeletal code based on
# socket_echo_server_dgram.py and socket_echo_client_dgram.py from https://pymotw.com/3/socket/udp.html
#
# each ringo acts as client and server; must find local and foreign addresses, bind local address to port

import socket
import sys
import time

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

def peerDiscovery(poc_addr, sock, message):
    try:

        # Send data
        print('sending {!r}'.format(message))
        sent = sock.sendto(message, poc_addr)

        # Receive response
        print('waiting to receive')
        data, server = sock.recvfrom(4096)
        print('received {!r}'.format(data))

    finally:
        print('closing socket')
        sock.close()
    


def msgSend(poc_addr, sock, message):
    try:

        # Send data
        print('sending {!r}'.format(message))
        sent = sock.sendto(message, poc_addr)

        # Receive response
        print('waiting to receive')
        data, server = sock.recvfrom(4096)
        print('received {!r}'.format(data))

    finally:
        print('closing socket')
        sock.close()

#     alive = True    # if user enters command "offline," this is set to false
#     while alive:
#         ### listen for commands
#         alive = False # remove after functionality added
#     return;

def msgReceive(sock):
    while True:
        print('\nwaiting to receive message')
        data, address = sock.recvfrom(4096)

        print('received {} bytes from {}'.format(
            len(data), address))
        print(data)

        if data:
            sent = sock.sendto(data, address)
            print('sent {} bytes back to {}'.format(
                sent, address))
#     alive = True    # if user enters command "offline," this is set to false
#     while alive:
#         ### listen for commands
#         alive = False # remove after functionality added
#     return;

# def msgForward():
#     alive = True    # if user enters command "offline," this is set to false
#     while alive:
#         ### listen for commands
#         alive = False # remove after functionality added
#     return;



def main():

    # tm = time.monotonic();
    # print(tm);
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

    message = "hello";

    if (role is "S"):
        msgSend(poc_addr, sock, message);

    elif (role is "F"):
        msgForward();

    elif (role is "R"):
        msgReceive(sock);


    


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
