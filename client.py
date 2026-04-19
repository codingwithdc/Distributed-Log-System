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

def simple_encrypt(text, key):
    return bytes([ord(c) ^ key for c in text])

def tail_file(filename):
    """Follow a log file in real-time (like 'tail -f')"""
    try:
        with open(filename, 'r') as f:
            # Go to end of file
            f.seek(0, os.SEEK_END)
            while True:
                line = f.readline()
                if line:
                    yield line.strip()
                else:
                    time.sleep(0.1)
    except PermissionError:
        print(f"[WARN] Permission denied: {filename}. Run with sudo for system logs.")
        yield None
    except Exception as e:
        print(f"[WARN] Cannot read {filename}: {e}")
        yield None

def get_log_level(line):
    """Determine log level from real log content"""
    line_lower = line.lower()
    if any(word in line_lower for word in ['error', 'fail', 'critical', 'panic', 'denied', 'refused']):
        return 'ERROR'
    elif any(word in line_lower for word in ['warn', 'warning']):
        return 'WARN'
    elif any(word in line_lower for word in ['info', 'start', 'stop', 'connected', 'authenticated']):
        return 'INFO'
    else:
        return 'DEBUG'

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

udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def send_log(level, message):
    global seq
    seq += 1
    timestamp = time.time()
    log = f"{client_id}|{seq}|{timestamp}|{level}|{message}"
    encrypted = simple_encrypt(log, key)
    packet = bytes([len(client_id)]) + client_id.encode() + encrypted
    udp.sendto(packet, (SERVER, UDP_PORT))
    
    # Print to console (truncated for readability)
    short_msg = message[:100] + "..." if len(message) > 100 else message
    print(f"[{client_id}] [{seq}] {level}: {short_msg}")

# REAL SYSTEM LOG SOURCES 

log_sources = []

# 1. SYSTEM LOGS (macOS - using log command)
if platform.system() == 'Darwin':
    print(f"[{client_id}] Monitoring REAL macOS system logs...")
    
    def macos_system_logs():
        """Real-time macOS system logs using log stream"""
        try:
            # Use log stream for real-time system logs
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

# 2. SYSTEM LOGS (Linux)
else:
    log_files = []
    # Common Linux system log locations
    for log_file in ['/var/log/syslog', '/var/log/auth.log', '/var/log/kern.log', '/var/log/dmesg']:
        if os.path.exists(log_file):
            log_files.append(log_file)
            print(f"[{client_id}] Monitoring REAL Linux log: {log_file}")
            
            def create_log_monitor(filename):
                def monitor():
                    for line in tail_file(filename):
                        if line:
                            level = get_log_level(line)
                            send_log(level, f"{os.path.basename(filename)}: {line}")
                return monitor
            
            for log_file in log_files:
                log_sources.append((log_file, create_log_monitor(log_file)))

# 3. AUTHENTICATION LOGS (SSH, sudo, login)
if platform.system() == 'Darwin':
    # macOS: Use log stream for auth events
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
else:
    # Linux: /var/log/auth.log
    if os.path.exists('/var/log/auth.log'):
        def linux_auth_logs():
            for line in tail_file('/var/log/auth.log'):
                if line:
                    send_log('AUTH', f"AUTH: {line}")
        log_sources.append(('Linux Auth Logs', linux_auth_logs))

# 4. NETWORK CONNECTION LOGS
if platform.system() == 'Darwin':
    def macos_network_logs():
        """Monitor network connection events"""
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

# 5. SECURITY/CRASH LOGS
if platform.system() == 'Darwin':
    def macos_crash_logs():
        """Monitor crash reports"""
        try:
            process = subprocess.Popen(
                ['log', 'stream', '--predicate', 'eventMessage contains "crash" OR eventMessage contains "panic"'],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1
            )
            for line in process.stdout:
                if line.strip():
                    send_log('CRASH', f"CRASH: {line.strip()}")
        except:
            pass
    log_sources.append(('macOS Crash Logs', macos_crash_logs))

# 6. PROCESS MONITORING
def monitor_process_events():
    """Monitor real process creation/termination"""
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
    else:
        # Linux: Use auditd or ps monitoring
        try:
            previous_processes = set()
            while True:
                result = subprocess.run(['ps', '-eo', 'pid,comm'], capture_output=True, text=True)
                current_processes = set(result.stdout.strip().split('\n')[1:])
                
                # New processes
                new_processes = current_processes - previous_processes
                for proc in new_processes:
                    if proc.strip():
                        send_log('PROCESS', f"NEW PROCESS: {proc.strip()}")
                
                # Terminated processes  
                terminated = previous_processes - current_processes
                for proc in terminated:
                    if proc.strip():
                        send_log('PROCESS', f"TERMINATED: {proc.strip()}")
                
                previous_processes = current_processes
                time.sleep(5)
        except:
            pass

# START ALL LOG MONITORS

print(f"\n[{client_id}] ========================================")
print(f"[{client_id}] STARTING SYSTEM LOG AGGREGATOR")
print(f"[{client_id}] ========================================")

# Start each log source in its own thread
for name, source_func in log_sources:
    thread = threading.Thread(target=source_func, daemon=True)
    thread.start()
    print(f"[{client_id}] Started: {name}")

# Start process monitor
process_thread = threading.Thread(target=monitor_process_events, daemon=True)
process_thread.start()
print(f"[{client_id}] Started: Process Monitor")

print(f"\n[{client_id}] ALL LOGGERS ACTIVE ")
print(f"[{client_id}] Waiting for system events...")
print(f"[{client_id}] Press Ctrl+C to stop\n")

# Keep main thread alive
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print(f"\n[{client_id}] Stopping...")
