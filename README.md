# Secure Distributed Log Aggregation System

A simple distributed system that collects and processes logs from multiple machines in real time using UDP sockets and TLS-secured authentication.

## Features

* UDP-based log streaming from multiple clients
* TLS-secured control server for client authentication
* Concurrent log processing using worker threads
* Queue-based **backpressure handling**
* **Time-ordered log processing**
* System **throughput monitoring (logs/sec)**

## System Architecture

Client machines first authenticate with the **TLS control server**, then send logs to the **UDP log server**.

```
Clients
   |
   | TLS Authentication
   v
TLS Control Server
   |
   | UDP Log Streaming
   v
UDP Log Server
   |
Queue (Backpressure)
   |
Worker Threads
   |
Log Processor
   |
Metrics (Throughput)
```

## Technologies Used

* Python
* UDP Socket Programming
* TLS / SSL (Python `ssl` module)
* Multithreading
* Queue-based buffering

## Project Structure

```
distributed_log_system
│
├── udp_server.py      # UDP log ingestion server
├── tls_server.py      # TLS authentication server
├── client.py          # log generating client
├── processor.py       # log ordering and processing
├── metrics.py         # throughput and drop statistics
├── generate_cert.sh   # script to generate TLS certificates
```

## Setup

### 1. Clone the repository

```
git clone <repo-url>
cd distributed_log_system
```

### 2. Generate TLS certificates

```
bash generate_cert.sh
```

### 3. Start servers

```
python udp_server.py
python tls_server.py
```

### 4. Run clients

```
python client.py client1
python client.py client2
```

## Example Output

```
[12:03:11] client1 INFO CPU high
[12:03:12] client2 WARN memory spike

---- METRICS ----
logs: 540
dropped: 2
throughput: 108 logs/sec
```
