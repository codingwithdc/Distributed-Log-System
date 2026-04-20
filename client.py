import socket
import ssl
import time
import sys
import os
import platform
import subprocess
import threading
from datetime import datetime

SERVER = "127.0.0.1"
TLS_PORT = 8000
UDP_PORT = 9000

client_id = sys.argv[1] if len(sys.argv) > 1 else socket.gethostname()
seq = 0

# Backpressure variables
current_interval = 0.5  # Start with 2 logs per second
min_interval = 0.05      # Fastest: 20 logs per second
max_interval = 2.0       # Slowest: 0.5 logs per second
backpressure_mode = False
last_backpressure_time = 0

def simple_encrypt(text, key):
    return bytes([ord(c) ^ key for c in text])

def tail_file(filename):
    try:
        with open(filename, 'r') as f:
            f.seek(0, os.SEEK_END)
            while True:
                line = f.readline()
                if line:
                    yield line.strip()
                else:
                    time.sleep(0.1)
    except:
        yield None

def get_log_level(line):
    line_lower = line.lower()
    if any(word in line_lower for word in ['error', 'fail', 'critical', 'panic', 'denied', 'refused']):
        return 'ERROR'
    elif any(word in line_lower for word in ['warn', 'warning']):
        return 'WARN'
    else:
        return 'INFO'

# Get encryption key via TLS
print(f"[{client_id}] Connecting to secure key server...")

context = ssl.create_default_context()
context.check_hostname = False
context.verify_mode = ssl.CERT_NONE

sock = socket.socket()
secure = context.wrap_socket(sock)
secure.connect((SERVER, TLS_PORT))

secure.send(client_id.encode())
key = int(secure.recv(1024).decode())
secure.close()

print(f"[{client_id}] Encryption key: {key}")
print(f"[{client_id}] OS: {platform.system()} {platform.release()}")

# Create UDP socket for sending logs AND receiving backpressure
udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp.setblocking(False)  # Non-blocking to check for backpressure messages

def send_log(level, message):
    global seq
    seq += 1
    timestamp = time.time()
    log = f"{client_id}|{seq}|{timestamp}|{level}|{message}"
    encrypted = simple_encrypt(log, key)
    packet = bytes([len(client_id)]) + client_id.encode() + encrypted
    udp.sendto(packet, (SERVER, UDP_PORT))
    
    short_msg = message[:80] + "..." if len(message) > 80 else message
    status = "BACKPRESSURE" if backpressure_mode else "NORMAL"
    print(f"[{client_id}] [{seq}] {status}: {level}: {short_msg}")

def listen_for_backpressure():
    """Listen for backpressure signals from server"""
    global current_interval, backpressure_mode, last_backpressure_time
    
    while True:
        try:
            data, _ = udp.recvfrom(1024)
            message = data.decode()
            
            if message.startswith("BACKPRESSURE:"):
                last_backpressure_time = time.time()
                backpressure_mode = True
                
                if "SLOW_DOWN" in message:
                    # Increase interval (slow down)
                    current_interval = min(current_interval + 0.2, max_interval)
                    print(f"\n[BACKPRESSURE] Server says SLOW DOWN! New interval: {current_interval:.2f}s")
                    
                elif "REDUCE_RATE" in message:
                    # Moderate slowdown
                    current_interval = min(current_interval + 0.1, max_interval)
                    print(f"\n[BACKPRESSURE] Server busy. New interval: {current_interval:.2f}s")
                    
                elif "WAIT" in message:
                    # Temporary pause
                    print(f"\n[BACKPRESSURE] Server requests wait")
                    
        except socket.error:
            # No message available
            pass
        
        # Gradually recover from backpressure (speed up)
        if backpressure_mode and (time.time() - last_backpressure_time) > 5:
            current_interval = max(current_interval - 0.05, min_interval)
            if current_interval <= min_interval:
                backpressure_mode = False
                print(f"\n[BACKPRESSURE] Recovery complete. Normal speed resumed.")
        
        time.sleep(0.1)

# Start backpressure listener thread
backpressure_thread = threading.Thread(target=listen_for_backpressure, daemon=True)
backpressure_thread.start()

# REAL SYSTEM LOG SOURCES
log_sources = []

if platform.system() == 'Darwin':
    print(f"[{client_id}] Monitoring REAL macOS system logs...")
    
    def macos_system_logs():
        try:
            process = subprocess.Popen(
                ['log', 'stream', '--style', 'syslog', '--level', 'info'],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1
            )
            for line in process.stdout:
                if line.strip():
                    level = get_log_level(line)
                    send_log(level, f"SYSTEM: {line.strip()}")
        except Exception as e:
            print(f"[ERROR] System log stream failed: {e}")
    
    log_sources.append(('macOS System Logs', macos_system_logs))
    
    def macos_auth_logs():
        try:
            process = subprocess.Popen(
                ['log', 'stream', '--predicate', 'subsystem == "com.apple.authd"'],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1
            )
            for line in process.stdout:
                if line.strip():
                    send_log('AUTH', f"AUTH: {line.strip()}")
        except:
            pass
    log_sources.append(('macOS Auth Logs', macos_auth_logs))
    
    def macos_network_logs():
        try:
            process = subprocess.Popen(
                ['log', 'stream', '--predicate', 'process == "kernel" AND (eventMessage contains "WiFi" OR eventMessage contains "en0")'],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1
            )
            for line in process.stdout:
                if line.strip():
                    send_log('NETWORK', f"NETWORK: {line.strip()}")
        except:
            pass
    log_sources.append(('macOS Network Logs', macos_network_logs))

def monitor_process_events():
    if platform.system() == 'Darwin':
        try:
            process = subprocess.Popen(
                ['log', 'stream', '--predicate', 'eventMessage contains "exited" OR eventMessage contains "launch"'],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1
            )
            for line in process.stdout:
                if line.strip():
                    send_log('PROCESS', f"PROCESS: {line.strip()}")
        except:
            pass

print(f"\n[{client_id}] ========================================")
print(f"[{client_id}] STARTING SYSTEM LOG AGGREGATOR")
print(f"[{client_id}] WITH BACKPRESSURE HANDLING")
print(f"[{client_id}] ========================================")

for name, source_func in log_sources:
    thread = threading.Thread(target=source_func, daemon=True)
    thread.start()
    print(f"[{client_id}] Started: {name}")

process_thread = threading.Thread(target=monitor_process_events, daemon=True)
process_thread.start()
print(f"[{client_id}] Started: Process Monitor")

print(f"\n[{client_id}] Current send interval: {current_interval:.2f}s")
print(f"[{client_id}] Backpressure listening active")
print(f"[{client_id}] Waiting for system events...\n")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print(f"\n[{client_id}] Stopping...")
