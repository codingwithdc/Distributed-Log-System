# Secure Log Aggregation System

## Overview

This project implements a secure and scalable log aggregation system where multiple clients send **real system logs** to a central server in real-time. The system combines TLS (for secure key exchange) with UDP (for high-speed transmission) and lightweight XOR encryption to balance security and performance. The server tracks **latency** and **packet loss** metrics, providing insight into network performance.

---

## Features

- **Secure key exchange** using TLS 1.2+
- **Fast log transmission** using UDP
- **Lightweight XOR-based encryption** for log confidentiality
- **Real system log collection** (macOS/Linux kernel logs, auth events, network events, crashes)
- **Multi-client support** with concurrent processing
- **Sequence number tracking** for detecting packet loss
- **Latency measurement** (average, min, max) for each log
- **Multithreaded log processing** (4 worker threads)
- **Performance monitoring** (throughput, latency, packet loss, active clients)
- **Backpressure handling** 

---

## Setup Instructions

1. Generate Certificates

chmod +x generate_cert.sh
./generate_cert.sh

Or manually:
openssl req -new -x509 -days 365 -nodes -out server.crt -keyout server.key -subj "/CN=127.0.0.1"


2. Start Server

python3 server.py

3. Run Client(s)

Terminal 2
python3 client.py client1

Terminal 3
python3 client.py client2
