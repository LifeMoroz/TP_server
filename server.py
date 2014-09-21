import socket
import select
import datetime
from sendfile import sendfile
import os

EOL1 = b'\n\n'
EOL2 = b'\n\r\n'
response = b'HTTP/1.0 200 OK\r\nDate: Mon, 1 Jan 1996 01:01:01 GMT\r\n'
response += b'Content-Type: text/plain\r\nContent-Length: 13\r\n\r\n'
response += b'Hello, world!'

serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
serversocket.bind(('127.0.0.1', 8080))
serversocket.listen(128)
serversocket.setblocking(0)
serversocket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

epoll = select.epoll()
epoll.register(serversocket.fileno(), select.EPOLLIN)
code = 000
try:
    connections = {}
    requests = {}
    responses = {}
    while True:
        events = epoll.poll(1)
        for fileno, event in events:
            if fileno == serversocket.fileno():
                connection, address = serversocket.accept()
                connection.setblocking(0)
                epoll.register(connection.fileno(), select.EPOLLIN)
                connections[connection.fileno()] = connection
                requests[connection.fileno()] = b''
                response = {'version': b'HTTP/1.1 ',
                            'Date': datetime.datetime.now().strftime("Date: %d.%m.%Y %H:%M:%p GMT"),
                            'Server': 'Ruslan Server 0.1a'}
                responses[connection.fileno()] = {'headers': response, 'file': None}
            elif event & select.EPOLLIN:
                data = connections[fileno].recv(1024)
                if not data:
                    epoll.modify(fileno, select.EPOLLET)
                    connections[fileno].shutdown(socket.SHUT_RDWR)
                else:
                    requests[fileno] += data
                if EOL1 in requests[fileno] or EOL2 in requests[fileno]:
                    epoll.modify(fileno, select.EPOLLOUT)
                    print requests[fileno].split('\r\n')
                    #print('-' * 40 + '\n' + requests[fileno].decode()[:-2])
            elif event & select.EPOLLOUT:
                response = responses[fileno]['headers']['version']
                if os.path.isfile(response[fileno]['file']):
                    response[fileno]['headers']['Content-type'] = {
                        #http://tool.oschina.net/commons
                        'html': 'text/html',
                        'jpg':  'image/jpeg',
                        'jpeg': 'image/jpeg',
                        'css':  'text/css',
                        'png':  'image/png',
                        'gif':  'image/gif',
                        'swf':  'application/x-shockwave-flash'
                    }[response[fileno]['file'].split('.')[-1]]
                byteswritten = connections[fileno].send(response)
                responses[fileno] = {}
                if responses[fileno].get("file"):
                    sendfile(connections[fileno], open(responses[fileno].get("file")),
                             os.path.getsize(responses[fileno].get("file")))
                if len(response) >= 0:
                    epoll.modify(fileno, 0)
                    connections[fileno].shutdown(socket.SHUT_RDWR)
            elif event & select.EPOLLHUP:
                epoll.unregister(fileno)
                connections[fileno].close()
                del connections[fileno]
finally:
    epoll.unregister(serversocket.fileno())
    epoll.close()
    serversocket.close()
