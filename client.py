import asyncore
import socket
from threading import Thread
import time


class HTTPClient(asyncore.dispatcher):
    def __init__(self, host, path, port=8080):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect((host, 8080))
        self.buffer = 'GET %s HTTP/1.1\r\n\r\n' % path

    def handle_connect(self):
        pass

    def handle_close(self):
        self.close()

    def handle_read(self):
        print self.recv(8192)

    def writable(self):
        return (len(self.buffer) > 0)

    def handle_write(self):
        sent = self.send(self.buffer)
        self.buffer = self.buffer[sent:]

client = HTTPClient('127.0.0.1', '/index.html')

asyncore.loop()