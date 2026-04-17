# Secure Log Aggregation System

## Overview

This project implements a **secure and scalable log aggregation system** where multiple clients send log data to a central server. The system combines **TLS (for secure key exchange)** with **UDP (for high-speed transmission)** and **lightweight encryption** to balance security and performance.

---

## Features

* Secure key exchange using TLS
* Fast log transmission using UDP
* Lightweight XOR-based encryption for logs
* Multi-client support
* Sequence tracking for detecting packet loss
* Multithreaded log processing
* Performance monitoring (throughput, dropped logs, active clients)

---

## Architecture

### Components

1. **Server (`server.py`)**

   * Handles TLS connections for key exchange
   * Receives encrypted logs over UDP
   * Decrypts and processes logs
   * Maintains metrics

2. **Client (`client.py`)**

   * Connects via TLS to obtain encryption key
   * Generates logs continuously
   * Encrypts logs using XOR
   * Sends logs via UDP

3. **Testing Scripts**

   * `verify_encryption.sh` → checks if logs are encrypted
   * `test_dtls.py` → tests encryption and throughput

4. **Certificate Generator**

   * `generate_cert.sh` → generates TLS certificate and private key

---

## Workflow

1. Client connects to server using TLS
2. Server assigns a symmetric XOR key
3. Client encrypts logs using the key
4. Logs are sent over UDP
5. Server decrypts and processes logs
6. Metrics are displayed periodically

---

## Security Model

* TLS ensures secure key exchange using public/private key cryptography
* XOR encryption secures log messages during UDP transmission
* Hybrid model balances **security (TLS)** and **performance (UDP)**

---

## Setup Instructions

### 1. Generate Certificates

```bash
chmod +x generate_cert.sh
./generate_cert.sh
```

### 2. Start Server

```bash
python3 server.py
```

### 3. Run Client(s)

```bash
python3 client.py client1
python3 client.py client2
```

---

## Testing

### Encryption Verification

```bash
chmod +x verify_encryption.sh
./verify_encryption.sh
```

### Throughput Test

```bash
python3 test_dtls.py
```

---

## Metrics Displayed

* Total logs processed
* Dropped logs
* Throughput (logs/sec)
* Number of active clients

---

## Limitations

* XOR encryption is not secure for real-world applications
* Uses self-signed certificates (no authentication)
* UDP does not guarantee delivery

---

## Summary

This project demonstrates how to design a **secure yet high-performance logging system** by combining secure key exchange with fast data transmission, making it a practical example of real-world distributed systems design.
