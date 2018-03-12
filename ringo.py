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


def main():
	role = ""
	if (len(sys.argv) != 6):
		usage();
    if (sys.argv[1]=="S"):
    	role = "S"





	print "Made it so far!"
	

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