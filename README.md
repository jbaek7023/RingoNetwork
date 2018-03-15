# RingoNetwork

# System gets the arguments
	ringo S aposdpasda
	# interpret the argument
	S:  # it’s like a client (Listen for distance vector BUT not listening for data// sending data)
		-> Peer Discovery
		open thread and listen for user input.

	R:  # It’s like a server (Listen for distance vector But Listening for data / not send data)
		-> Peer Discovery # Listen for peer discovery - Listen for Keep Alive Signal

	F: (Listen for distance vector listen for data and send data)
		-> Peer DIscovery

# 
———>offline, send, show-matrix-, show-ring, disconnect.


RTT
These are the tests conducted on the way to peer discovery:
1) 2 nodes, 1 peer each, send message
	found error in approach; only bind local socket
	successful