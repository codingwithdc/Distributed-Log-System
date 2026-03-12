import socket
import ssl
import time
import random
import sys

SERVER="127.0.0.1"

UDP_PORT=9000
TLS_PORT=8000

client_id=sys.argv[1] if len(sys.argv)>1 else "client1"

# TLS handshake

context=ssl.create_default_context()
context.check_hostname=False
context.verify_mode=ssl.CERT_NONE

sock=socket.socket()

tls=context.wrap_socket(sock)

tls.connect((SERVER,TLS_PORT))

tls.recv(1024)

tls.close()

print("secure session established")

# UDP log streaming

udp=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)

levels=["INFO","WARN","ERROR"]

msgs=[
"CPU high",
"disk full",
"memory spike",
"service restart",
"network delay"
]

while True:

    log=f"{client_id}|{time.time()}|{random.choice(levels)}|{random.choice(msgs)}"

    udp.sendto(log.encode(),(SERVER,UDP_PORT))

    time.sleep(random.uniform(0.1,1))