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

s.sendto(file_name,addr)