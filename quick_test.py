import socket
import ssl
import time
import sys
import threading

SERVER = "127.0.0.1"
TLS_PORT = 8000
UDP_PORT = 9000

client_id = sys.argv[1] if len(sys.argv) > 1 else "test_client"

current_interval = 0.1  # Start fast (10 logs/sec)
min_interval = 0.05
max_interval = 2.0
backpressure_mode = False
last_backpressure_time = 0

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
udp.setblocking(False)

def listen_for_backpressure():
    global current_interval, backpressure_mode, last_backpressure_time
    while True:
        try:
            data, _ = udp.recvfrom(1024)
            message = data.decode()
            if "BACKPRESSURE:" in message:
                last_backpressure_time = time.time()
                backpressure_mode = True
                if "SLOW_DOWN" in message:
                    current_interval = min(current_interval + 0.2, max_interval)
                    print(f"\n[BACKPRESSURE] Slowing down to {current_interval:.2f}s intervals")
                elif "REDUCE_RATE" in message:
                    current_interval = min(current_interval + 0.1, max_interval)
                    print(f"\n[BACKPRESSURE] Reducing rate to {current_interval:.2f}s")
        except:
            pass
        
        if backpressure_mode and (time.time() - last_backpressure_time) > 5:
            current_interval = max(current_interval - 0.05, min_interval)
            if current_interval <= min_interval:
                backpressure_mode = False
                print(f"\n[BACKPRESSURE] Resumed normal speed")
        time.sleep(0.1)

threading.Thread(target=listen_for_backpressure, daemon=True).start()

seq = 0
print(f"[{client_id}] Sending logs with backpressure handling...")

while True:
    seq += 1
    log = f"{client_id}|{seq}|{time.time()}|TEST|Quick test message {seq}"
    encrypted = simple_encrypt(log, key)
    packet = bytes([len(client_id)]) + client_id.encode() + encrypted
    udp.sendto(packet, (SERVER, UDP_PORT))
    
    status = "slow" if backpressure_mode else "fast"
    print(f"{status} [{client_id}] Sent [{seq}] (interval: {current_interval:.2f}s)")
    time.sleep(current_interval)
