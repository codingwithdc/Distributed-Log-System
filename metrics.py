import time

class Metrics:

    def __init__(self):
        self.start=time.time()
        self.logs=0
        self.dropped=0

    def received(self):
        self.logs+=1

    def drop(self):
        self.dropped+=1

    def report(self):

        elapsed=time.time()-self.start

        throughput=self.logs/elapsed if elapsed>0 else 0

        print("\n---- METRICS ----")
        print("logs:",self.logs)
        print("dropped:",self.dropped)
        print("throughput:",round(throughput,2),"logs/sec")
        print("-----------------\n")