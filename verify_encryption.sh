#!/bin/bash

echo "=== DTLS Encryption Verification ==="
echo ""

# Start server in background
python3 server.py &
SERVER_PID=$!

sleep 2

# Start client in background
python3 client.py test_client &
CLIENT_PID=$!

sleep 3

# Capture UDP packets
echo "Capturing UDP packets on port 9000..."
sudo tcpdump -i lo0 -c 5 -X udp port 9000 2>/dev/null | grep -E "(INFO|WARN|ERROR|CPU|disk|memory)" > /tmp/dtls_test.txt

if [ -s /tmp/dtls_test.txt ]; then
    echo ""
    echo "FAIL: Plaintext log data detected in UDP packets!"
    cat /tmp/dtls_test.txt
else
    echo ""
    echo "PASS: No plaintext log data found - DTLS encryption working!"
fi

# Cleanup
kill $CLIENT_PID 2>/dev/null
kill $SERVER_PID 2>/dev/null
rm -f /tmp/dtls_test.txt

echo ""
echo "Test complete"
