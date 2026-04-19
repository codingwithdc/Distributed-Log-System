import socket
import ssl
import time
import sys

SERVER = "127.0.0.1"  # or "localhost"
TLS_PORT = 8000
UDP_PORT = 9000

client_id = sys.argv[1] if len(sys.argv) > 1 else "test_client"

def simple_encrypt(text, key):
    return bytes([ord(c) ^ key for c in text])

# Get key
context = ssl.create_default_context()
context.check_hostname = False
context.verify_mode = ssl.CERT_NONE

sock = socket.socket()
secure = context.wrap_socket(sock)
secure.connect((SERVER, TLS_PORT))

secure.send(client_id.encode())
key = int(secure.recv(1024).decode())
secure.close()

print(f"[{client_id}] Key: {key}")

udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

seq = 0
while True:
    seq += 1
    log = f"{client_id}|{seq}|{time.time()}|TEST|Quick test message {seq}"
    encrypted = simple_encrypt(log, key)
    packet = bytes([len(client_id)]) + client_id.encode() + encrypted
    udp.sendto(packet, (SERVER, UDP_PORT))
    print(f"Sent: {log}")
    time.sleep(1)
