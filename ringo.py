# RDT Ringo
#
# a Ringo node using the Reliable Data Transfer protocol, using skeletal code based on
# socket_echo_server_dgram.py and socket_echo_client_dgram.py from https://pymotw.com/3/socket/udp.html

import socket
import sys

def usage():
    print """Usage:
        python ringo.py <flag> <local-port> <PoC-name> <PoC-port> <N> """
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

def check_numeric(idx, val, arg):
    try:
   	    val = int(sys.argv[idx])
    except ValueError:
	    print(arg + " must be an int")
	    sys.exit(1)



def main():
    role = ""		# job of ringo (sender, receiver, forwarder)
    cmd = ""		# command received from user while living
    
    n_size, l_port, poc_port = 0, 0, 0	# size of network, local port #, poc port #

    if (len(sys.argv) != 6):
        usage();

    check_flag(role);

    check_numeric(2, l_port, "local-port");

    check_numeric(4, poc_port, "PoC-port");

    check_numeric(5, n_size, "N");

    # # Create a UDP socket
    # sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	
    # # Bind the socket to the port
    # # 'localhosts' should be changed before testing on network
    # local_address = ('localhost', l_port)    
    # poc_address = ('localhost', poc_port)
    # print('starting up on {} port {}'.format(*local_address))
    # sock.bind(local_address)



    ### Seems like threads should be used to listen and speak to ports for message, listen and speak to ports for "keep-alives",
    ### and listen for commands; 


    alive = True	# if user enters command "offline," this is set to false
    while alive:
    	### listen for commands

    	alive = False # remove after functionality added


    print "Made it this far..."
	

# # Create a UDP socket
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