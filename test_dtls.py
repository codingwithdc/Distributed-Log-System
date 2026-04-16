import subprocess
import threading
import time
import socket
import sys

def run_client(client_id, duration):
    """Run a client for specified duration"""
    proc = subprocess.Popen(
        [sys.executable, "client.py", client_id],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    time.sleep(duration)
    proc.terminate()
    return client_id

def test_encryption():
    """Verify that logs are actually encrypted"""
    print("\n" + "="*60)
    print("ENCRYPTION VERIFICATION TEST")
    print("="*60)
    
    # Sniff UDP packets
    def sniff_packets():
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_UDP)
        sock.settimeout(2)
        try:
            data, addr = sock.recvfrom(4096)
            print(f"\n[SNIFFER] Captured UDP packet (encrypted): {data[:50]}...")
            
            # Try to decode as text - should fail or look like garbage
            try:
                decoded = data.decode('utf-8')
                if any(word in decoded for word in ["INFO", "WARN", "ERROR", "CPU", "disk"]):
                    print("[FAIL] ❌ Logs are PLAINTEXT - NOT secure!")
                    return False
                else:
                    print("[PASS] ✅ Logs appear encrypted (garbled data)")
            except:
                print("[PASS] ✅ Logs are encrypted (cannot decode as UTF-8)")
            return True
        except socket.timeout:
            print("[INFO] No packets captured (run client first)")
            return None
    
    print("Starting sniffer (requires root)...")
    print("Run client in another terminal, then check results")
    return sniff_packets()

def throughput_test():
    """Test with multiple concurrent clients"""
    print("\n" + "="*60)
    print("THROUGHPUT TEST")
    print("="*60)
    
    client_counts = [1, 5, 10, 25]
    duration = 20
    
    for num_clients in client_counts:
        print(f"\nTesting with {num_clients} clients for {duration} seconds...")
        
        threads = []
        for i in range(num_clients):
            t = threading.Thread(target=run_client, args=(f"client{i}", duration))
            t.start()
            threads.append(t)
            time.sleep(0.2)  # Stagger start
        
        time.sleep(duration + 2)
        
        for t in threads:
            t.join()
        
        print(f"✓ Completed {num_clients} client test")
        time.sleep(3)

if __name__ == "__main__":
    print("\nDTLS SECURE LOG AGGREGATION SYSTEM")
    print("==================================")
    
    choice = input("\nSelect test:\n1. Encryption verification\n2. Throughput test\n3. Both\nChoice: ")
    
    if choice in ['1', '3']:
        test_encryption()
    
    if choice in ['2', '3']:
        throughput_test()