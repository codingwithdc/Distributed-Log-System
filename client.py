import socket
import ssl
import time
import random
import sys

SERVER = "127.0.0.1"
TLS_PORT = 8000
UDP_PORT = 9000

client_id = sys.argv[1] if len(sys.argv) > 1 else "client1"
seq = 0

def simple_encrypt(text, key):
    """Simple XOR encryption"""
    return bytes([ord(c) ^ key for c in text])

# Get encryption key via TLS
print(f"[{client_id}] Getting encryption key...")

context = ssl.create_default_context()
context.check_hostname = False
context.verify_mode = ssl.CERT_NONE

sock = socket.socket()
secure = context.wrap_socket(sock)
secure.connect((SERVER, TLS_PORT))

secure.send(client_id.encode())
key = int(secure.recv(1024).decode())
secure.close()

print(f"[{client_id}] Got encryption key: {key}")

# Start sending encrypted logs
udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

logs = [
    "CPU high",
    "disk full",
    "memory spike", 
    "service restart",
    "network delay"
]
levels = ["INFO", "WARN", "ERROR"]

print(f"[{client_id}] Sending encrypted logs...")

while True:
    seq += 1
    log = f"{client_id}|{seq}|{time.time()}|{random.choice(levels)}|{random.choice(logs)}"
    
    # Encrypt
    encrypted = simple_encrypt(log, key)
    
    # Send with client ID prefix
    packet = bytes([len(client_id)]) + client_id.encode() + encrypted
    udp.sendto(packet, (SERVER, UDP_PORT))
    
    print(f"[{client_id}] Sent: {log.split('|')[-2]} {log.split('|')[-1]}")
    time.sleep(random.uniform(0.1, 0.5))
