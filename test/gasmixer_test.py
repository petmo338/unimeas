import zmq
import logging
import threading
from time import sleep

POLL_TIMEOUT = 10

class Publisher(threading.Thread):
    def __init__(self):
        super(Publisher, self).__init__()
        try:
            self.context = zmq.Context().instance()
            self.socket = self.context.socket(zmq.PUB)
            self.socket.bind('tcp://*:5561')
            self.syncservice = self.context.socket(zmq.REP)
            self.syncservice.bind('tcp://*:5562')
            self.poller = zmq.Poller()
            self.poller.register(self.syncservice, zmq.POLLIN)
        except:
            return None
        self.running = True

    def run(self):
        while self.running:
            self.socket.send('HEARTBEAT')
            socks = dict(self.poller.poll(POLL_TIMEOUT))
            if self.syncservice in socks and socks[self.syncservice] == zmq.POLLIN:
                msg = self.syncservice.recv()
                if msg.find('CONNECT') != -1:
                    self.syncservice.send('CONFIG{\"0\": \"Reg1\", \"1\": \"Reg2\"}')

            sleep(1)
# def main():
#     context = zmq.Context()
#
#     # Socket to talk to clients
#     publisher = context.socket(zmq.PUB)
#     # set SNDHWM, so we don't drop messages for slow subscribers
#     # publisher.sndhwm = 1100000
#     publisher.bind('tcp://localhost:5561')
#
#     # Socket to receive signals
#     syncservice = context.socket(zmq.REP)
#     syncservice.bind('tcp://*:5562')
#
#     # Get synchronization from subscribers
#     subscribers = 0
#     while subscribers < SUBSCRIBERS_EXPECTED:
#         # wait for synchronization request
#         msg = syncservice.recv()
#         # send synchronization reply
#         syncservice.send(b'')
#         subscribers += 1
#         print("+1 subscriber (%i/%i)" % (subscribers, SUBSCRIBERS_EXPECTED))
#
#     # Now broadcast exactly 1M updates followed by END
#     for i in range(1000000):
#         publisher.send(b'Rhubarb')
#
#     publisher.send(b'END')

if __name__ == '__main__':
    p = Publisher()
    p.start()
    sleep(10)
    p.running = False
    p.join
