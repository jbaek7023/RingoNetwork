# left = input('> ')
# print(left)
# print(left[0])
# print(left.split()[1])

from socket import *
import sys

s = socket(AF_INET,SOCK_DGRAM)
host =sys.argv[1]
port = 9999
buf =1024
addr = (host,port)

file_name=input('> ')

s.sendto(file_name.encode(),addr)
f = open(file_name,'rb')
data = f.read(buf)
while(data):
	if(s.sendto(data,addr)):
		print('sent:\t' + data.decode())
		data = f.read(buf)
s.close()
f.close()