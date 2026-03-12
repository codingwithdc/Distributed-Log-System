import socket
import threading
import queue
import time

from processor import process
from metrics import Metrics

HOST="0.0.0.0"
PORT=9000
BUFFER=1024
QUEUE_SIZE=5000

log_queue=queue.Queue(maxsize=QUEUE_SIZE)
metrics=Metrics()


def worker():

    while True:

        log=log_queue.get()

        process(log)

        log_queue.task_done()


def monitor():

    while True:

        time.sleep(5)

        metrics.report()


def start():

    s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)

    s.bind((HOST,PORT))

    print("UDP log server running")

    while True:

        data,addr=s.recvfrom(BUFFER)

        log=data.decode()

        try:

            log_queue.put(log,block=False)

            metrics.received()

        except queue.Full:

            metrics.drop()


if __name__=="__main__":

    for i in range(4):
        threading.Thread(target=worker,daemon=True).start()

    threading.Thread(target=monitor,daemon=True).start()

    start()