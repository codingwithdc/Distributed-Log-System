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

# LATENCY & PACKET LOSS METRICS
total_latency_ms = 0  # Sum of all latencies for averaging
latency_count = 0     # Number of latency measurements
max_latency_ms = 0    # Maximum latency observed
min_latency_ms = float('inf')  # Minimum latency observed

total_expected = 0  
total_received = 0 

def simple_encrypt(text, key):
    """Simple XOR encryption (reversible)"""
    return bytes([ord(c) ^ key for c in text])

def simple_decrypt(data, key):
    """Decrypt XOR encrypted data"""
    return ''.join([chr(b ^ key) for b in data])

def process_log(log_data, receive_time):
    global processed, total_latency_ms, latency_count, max_latency_ms, min_latency_ms
    global total_expected, total_received
    
    try:
        client_id, seq, ts, level, msg = log_data.split("|", 4)
        seq = int(seq)
        send_ts = float(ts)
        
        # LATENCY CALCULATION (in milliseconds)
        latency_ms = (receive_time - send_ts) * 1000
        total_latency_ms += latency_ms
        latency_count += 1
        
        if latency_ms > max_latency_ms:
            max_latency_ms = latency_ms
        if latency_ms < min_latency_ms:
            min_latency_ms = latency_ms
        
        # PACKET LOSS DETECTION using sequence numbers
        if client_id in client_seq:
            expected_seq = client_seq[client_id] + 1
            if seq != expected_seq:
                lost = seq - expected_seq
                total_expected += lost
                print(f"[LOSS] {client_id}: lost {lost} packet(s) (expected {expected_seq}, got {seq})")
        
        client_seq[client_id] = seq
        total_received += 1
        total_expected += 1
        
        # Display log
        time_str = datetime.fromtimestamp(send_ts).strftime('%H:%M:%S.%f')[:-3]
        print(f"[{time_str}] {client_id} [{level}] {msg[:80]}")
        processed += 1
        
    except Exception as e:
        print(f"[ERROR] Process: {e}")

def worker():
    while True:
        log, receive_time = log_queue.get()
        process_log(log, receive_time)
        log_queue.task_done()

def udp_server():
    global dropped
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, UDP_PORT))
    print(f"[UDP] Listening on port {UDP_PORT}")
    
    while True:
        data, addr = sock.recvfrom(65535)
        receive_time = time.time()
        
        id_len = data[0]
        client_id = data[1:1+id_len].decode()
        
        if client_id not in client_keys:
            dropped += 1
            continue
        
        encrypted = data[1+id_len:]
        decrypted = simple_decrypt(encrypted, client_keys[client_id])
        
        try:
            log_queue.put((decrypted, receive_time), block=False)
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
        key = hash(client_id) % 255 + 1
        client_keys[client_id] = key
        conn.send(str(key).encode())
        print(f"[AUTH] {client_id} from {addr} (key: {key})")
    except:
        pass
    finally:
        conn.close()

def monitor():
    global min_latency_ms, max_latency_ms
    
    while True:
        time.sleep(10)
        elapsed = time.time() - start_time
        throughput = processed / elapsed if elapsed > 0 else 0
        
        # Calculate average latency
        avg_latency_ms = total_latency_ms / latency_count if latency_count > 0 else 0
        
        # Reset min/max if no data
        if latency_count == 0:
            min_latency_ms = 0
            max_latency_ms = 0
        
        # Calculate packet loss percentage
        packet_loss_percent = 0
        if total_expected > 0:
            packet_loss_percent = ((total_expected - total_received) / total_expected) * 100
        
        print("\n" + "="*50)
        print("METRICS REPORT")
        print("="*50)
        print(f"Logs processed: {processed}")
        print(f"Logs dropped (queue full): {dropped}")
        print(f"Throughput: {throughput:.2f} logs/sec")
        print(f"\nLATENCY:")
        print(f"   Average: {avg_latency_ms:.2f} ms")
        print(f"   Minimum: {min_latency_ms:.2f} ms")
        print(f"   Maximum: {max_latency_ms:.2f} ms")
        print(f"\nPACKET LOSS:")
        print(f"   Expected packets: {total_expected}")
        print(f"   Received packets: {total_received}")
        print(f"   UDP Loss rate: {packet_loss_percent:.2f}%")
        print(f"\nActive clients: {len(client_keys)}")
        print("="*50 + "\n")

# Start threads
for _ in range(4):
    threading.Thread(target=worker, daemon=True).start()

threading.Thread(target=udp_server, daemon=True).start()
threading.Thread(target=monitor, daemon=True).start()

print("\n" + "="*50)
print("REAL SYSTEM LOG AGGREGATOR")
print("WITH LATENCY & PACKET LOSS METRICS")
print("="*50)
tls_server()
