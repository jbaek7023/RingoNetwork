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
		-> Peer Discovery

#
———>offline, send, show-matrix-, show-ring, disconnect.
