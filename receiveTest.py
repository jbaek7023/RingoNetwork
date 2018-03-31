from socket import *
import sys
import select

host="127.0.0.1"
port = 9999
s = socket(AF_INET,SOCK_DGRAM)
s.bind((host,port))

addr = (host,port)
buf=1024

data,addr = s.recvfrom(buf)
print "Received File:",data.strip()
# f = open(data.strip(),'wb')