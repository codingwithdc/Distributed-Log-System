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
BACKPRESSURE_THRESHOLD = 4000  # 80% of queue size

# Store encryption keys for each client
client_keys = {}
client_seq = {}
client_addresses = {}

# Log processing queue
log_queue = queue.Queue(maxsize=QUEUE_SIZE)

# Metrics
processed = 0
dropped = 0
backpressure_signals_sent = 0
start_time = time.time()

# LATENCY & PACKET LOSS METRICS
total_latency_ms = 0
latency_count = 0
max_latency_ms = 0
min_latency_ms = float('inf')

total_expected = 0
total_received = 0

# UDP socket for sending backpressure signals
udp_sock = None
last_backpressure_time = {}

def simple_encrypt(text, key):
    return bytes([ord(c) ^ key for c in text])

def simple_decrypt(data, key):
    return ''.join([chr(b ^ key) for b in data])

def send_backpressure_signal(client_addr, reason):
    """Send backpressure signal to client"""
    global backpressure_signals_sent
    
    # Avoid spamming the same client too frequently
    current_time = time.time()
    client_key = f"{client_addr[0]}:{client_addr[1]}"
    
    if client_key in last_backpressure_time:
        if current_time - last_backpressure_time[client_key] < 0.5:
            return
    
    last_backpressure_time[client_key] = current_time
    
    try:
        if reason == "QUEUE_FULL":
            message = b"BACKPRESSURE:SLOW_DOWN"
        elif reason == "HIGH_LATENCY":
            message = b"BACKPRESSURE:REDUCE_RATE"
        else:
            message = b"BACKPRESSURE:WAIT"
        
        udp_sock.sendto(message, client_addr)
        backpressure_signals_sent += 1
        print(f"[BACKPRESSURE] Sent '{message.decode()}' to {client_addr} (queue: {log_queue.qsize()}/{QUEUE_SIZE})")
    except Exception as e:
        print(f"[ERROR] Backpressure send failed: {e}")

def process_log(log_data, receive_time, client_addr):
    global processed, total_latency_ms, latency_count, max_latency_ms, min_latency_ms
    global total_expected, total_received
    
    try:
        client_id, seq, ts, level, msg = log_data.split("|", 4)
        seq = int(seq)
        send_ts = float(ts)
        
        # Store client address
        if client_id not in client_addresses:
            client_addresses[client_id] = client_addr
        
        # LATENCY CALCULATION
        latency_ms = (receive_time - send_ts) * 1000
        total_latency_ms += latency_ms
        latency_count += 1
        
        if latency_ms > max_latency_ms:
            max_latency_ms = latency_ms
        if latency_ms < min_latency_ms:
            min_latency_ms = latency_ms
        
        # PACKET LOSS DETECTION
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
        log, receive_time, client_addr = log_queue.get()
        process_log(log, receive_time, client_addr)
        log_queue.task_done()

def udp_server():
    global dropped, udp_sock
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.bind((HOST, UDP_PORT))
    print(f"[UDP] Listening on port {UDP_PORT}")
    print(f"[BACKPRESSURE] Threshold: {BACKPRESSURE_THRESHOLD}/{QUEUE_SIZE} ({BACKPRESSURE_THRESHOLD/QUEUE_SIZE*100:.0f}%)")
    
    while True:
        try:
            data, addr = udp_sock.recvfrom(65535)
            receive_time = time.time()
            
            # Check for client recovery notification
            if data.startswith(b"BACKPRESSURE_RECOVERED"):
                print(f"[CLIENT] {addr}: Recovered from backpressure")
                continue
            
            id_len = data[0]
            client_id = data[1:1+id_len].decode()
            
            if client_id not in client_keys:
                dropped += 1
                continue
            
            encrypted = data[1+id_len:]
            decrypted = simple_decrypt(encrypted, client_keys[client_id])
            
            # ============================================================
            # BACKPRESSURE CHECK - BEFORE trying to put in queue!
            # ============================================================
            queue_size = log_queue.qsize()
            queue_percentage = (queue_size / QUEUE_SIZE) * 100
            
            # Send backpressure signals BEFORE queue becomes full
            if queue_percentage >= 95:
                send_backpressure_signal(addr, "QUEUE_FULL")
            elif queue_percentage >= BACKPRESSURE_THRESHOLD:
                send_backpressure_signal(addr, "HIGH_LATENCY")
            
            # Try to add to queue
            try:
                log_queue.put((decrypted, receive_time, addr), block=False)
            except queue.Full:
                dropped += 1
                send_backpressure_signal(addr, "QUEUE_FULL")
                print(f"[DROP] Queue full! Dropped packet from {addr}")
                
        except Exception as e:
            print(f"[UDP Error] {e}")

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
        
        avg_latency_ms = total_latency_ms / latency_count if latency_count > 0 else 0
        
        if latency_count == 0:
            min_latency_ms = 0
            max_latency_ms = 0
        
        packet_loss_percent = 0
        if total_expected > 0:
            packet_loss_percent = ((total_expected - total_received) / total_expected) * 100
        
        queue_percentage = (log_queue.qsize() / QUEUE_SIZE) * 100
        
        print("\n" + "="*60)
        print("METRICS REPORT")
        print("="*60)
        print(f"Logs processed: {processed}")
        print(f"Queue drops: {dropped}")
        print(f"Backpressure signals sent: {backpressure_signals_sent}")
        print(f"Throughput: {throughput:.2f} logs/sec")
        print(f"Queue status: {log_queue.qsize()}/{QUEUE_SIZE} ({queue_percentage:.0f}%)")
        print(f"\nLATENCY:")
        print(f"   Average: {avg_latency_ms:.2f} ms")
        print(f"   Minimum: {min_latency_ms:.2f} ms")
        print(f"   Maximum: {max_latency_ms:.2f} ms")
        print(f"\n PACKET LOSS:")
        print(f"   Expected packets: {total_expected}")
        print(f"   Received packets: {total_received}")
        print(f"   UDP Loss rate: {packet_loss_percent:.2f}%")
        print(f"\nActive clients: {len(client_keys)}")
        print("="*60 + "\n")

# Start threads
for _ in range(4):
    threading.Thread(target=worker, daemon=True).start()

threading.Thread(target=udp_server, daemon=True).start()
threading.Thread(target=monitor, daemon=True).start()

print("\n" + "="*50)
print("SECURE LOG AGGREGATOR WITH BACKPRESSURE")
print("="*50)
tls_server()
