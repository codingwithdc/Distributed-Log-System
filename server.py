import socket
import ssl
import threading
import queue
import time
from datetime import datetime

HOST = "0.0.0.0"
TLS_PORT = 8000
UDP_PORT = 9000
QUEUE_SIZE = 5000

# Store encryption keys for each client
client_keys = {}
client_seq = {}

# Log processing queue
log_queue = queue.Queue(maxsize=QUEUE_SIZE)

# Metrics
processed = 0
dropped = 0
start_time = time.time()

def simple_encrypt(text, key):
    """Simple XOR encryption (reversible)"""
    return bytes([ord(c) ^ key for c in text])

def simple_decrypt(data, key):
    """Decrypt XOR encrypted data"""
    return ''.join([chr(b ^ key) for b in data])

def process_log(log_data):
    global processed
    try:
        client_id, seq, ts, level, msg = log_data.split("|")
        seq = int(seq)
        
        # Track sequence numbers for ordering
        if client_id in client_seq:
            expected = client_seq[client_id] + 1
            if seq != expected:
                print(f"[WARN] {client_id}: expected {expected}, got {seq}")
        
        client_seq[client_id] = seq
        time_str = datetime.fromtimestamp(float(ts)).strftime('%H:%M:%S')
        print(f"[{time_str}] {client_id} [{level}] {msg}")
        processed += 1
    except:
        pass

def worker():
    while True:
        log = log_queue.get()
        process_log(log)
        log_queue.task_done()

def udp_server():
    global dropped
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, UDP_PORT))
    print(f"[UDP] Listening on port {UDP_PORT}")
    
    while True:
        data, addr = sock.recvfrom(4096)
        
        # First byte is client ID length, then client ID, then encrypted data
        id_len = data[0]
        client_id = data[1:1+id_len].decode()
        
        if client_id not in client_keys:
            dropped += 1
            continue
        
        # Decrypt using client's key
        encrypted = data[1+id_len:]
        decrypted = simple_decrypt(encrypted, client_keys[client_id])
        
        try:
            log_queue.put(decrypted, block=False)
        except queue.Full:
            dropped += 1

def tls_server():
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain("server.crt", "server.key")
    
    sock = socket.socket()
    sock.bind((HOST, TLS_PORT))
    sock.listen(5)
    secure = context.wrap_socket(sock, server_side=True)
    print(f"[TLS] Key exchange on port {TLS_PORT}")
    
    while True:
        conn, addr = secure.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

def handle_client(conn, addr):
    try:
        client_id = conn.recv(1024).decode()
        # Generate random key (1-255 for simple XOR)
        key = hash(client_id) % 255 + 1
        client_keys[client_id] = key
        conn.send(str(key).encode())
        print(f"[AUTH] {client_id} from {addr} (key: {key})")
    except:
        pass
    finally:
        conn.close()

def monitor():
    while True:
        time.sleep(10)
        elapsed = time.time() - start_time
        throughput = processed / elapsed if elapsed > 0 else 0
        print(f"\n[METRICS] Logs: {processed} | Dropped: {dropped} | Throughput: {throughput:.2f}/sec | Clients: {len(client_keys)}\n")

# Start threads
for _ in range(4):
    threading.Thread(target=worker, daemon=True).start()

threading.Thread(target=udp_server, daemon=True).start()
threading.Thread(target=monitor, daemon=True).start()

print("\n" + "="*50)
print("SECURE LOG SERVER RUNNING")
print("="*50)
tls_server()
