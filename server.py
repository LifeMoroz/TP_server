import logging
import socket
import select
import datetime
from sendfile import sendfile
import os
import urllib

EOL1 = b'\n\n'
EOL2 = b'\n\r\n'
ROOT = '/home/ruslan/.www'
LIST_METHODS = ['GET', 'HEAD']
NUMBER_OF_FORK = 4

serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
serversocket.bind(('127.0.0.1', 8080))
serversocket.listen(100)
serversocket.setblocking(0)
serversocket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

epoll = select.epoll()
epoll.register(serversocket.fileno(), select.EPOLLIN)
bad_code = {}

def get_header():
    response = b'Date:' + datetime.datetime.now().strftime("Date: %d.%m.%Y %H:%M:%p GMT\r\n") + \
               'Server: Ruslan Server 0.1a\r\n' \
               'Connection: close\r\n'
    if bad_code[fileno]:  # NOT OK and NOT 404
        response = b'HTTP/1.1 ' + bad_code[fileno] + '\r\n' + response + 'Content-type: text/plain\r\nContent-length: ' \
                   + str(len(bad_code[fileno])) + '\r\n\n' + bad_code[fileno]
        return response
    if responses[fileno]['body'] and os.path.isfile(responses[fileno]['body']):
        response = b'HTTP/1.1 200 OK\r\n' + response
    else:  # 404
        response = b'HTTP/1.1 404 Not Found\r\n' + response
        responses[fileno]['body'] = ROOT + '/404.html'
    try:
        response += 'Content-type: ' + {
            # http://tool.oschina.net/commons
            'html': 'text/html',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'js': 'text/javascript',
            'css': 'text/css',
            'png': 'image/png',
            'gif': 'image/gif',
            'swf': 'application/x-shockwave-flash'
        }[responses[fileno]['body'].split('.')[-1]] + '\r\n'
    except KeyError:
        response += 'Content-type: ' + 'text/plain\r\n'
    response += 'Content-Length: ' + str(os.path.getsize(responses[fileno]['body'])) + '\r\n\r\n'

    return response


def epoll_close():
    epoll.unregister(serversocket.fileno())
    epoll.close()
    serversocket.close()

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
                responses[connection.fileno()] = None  # ROOT + '/index.html'

            elif event & select.EPOLLIN:
                data = connections[fileno].recv(1024)
                if not data:
                    epoll.modify(fileno, select.EPOLLET)
                    connections[fileno].shutdown(socket.SHUT_RDWR)
                else:
                    requests[fileno] += data
                if EOL1 in requests[fileno] or EOL2 in requests[fileno]:
                    epoll.modify(fileno, select.EPOLLOUT)
                    #  print requests[fileno]
                    request_params = requests[fileno].split('\r\n')[0].split(" ")  # responses[fileno] = ROOT +
                    if len(request_params) < 3 or not request_params[0] in LIST_METHODS:
                        bad_code[fileno] = '400 Bad Request'
                    elif not request_params[0] in LIST_METHODS:
                        bad_code[fileno] = '405 Method Not Allowed'
                    else:
                        bad_code[fileno] = ''
                        responses[fileno] = {}
                        responses[fileno]['method'] = request_params[0]
                        responses[fileno]['body'] = ''.join(request_params[1:-1])
                        responses[fileno]['body'] = responses[fileno]['body'].split('?')[0]
                        if responses[fileno]['body'][-1] == "/":
                            responses[fileno]['body'] += "index.html"
                        responses[fileno]['body'] = os.path.normpath(
                            ROOT + responses[fileno]['body']).find("/home/ruslan/.www") == 0 and \
                            os.path.normpath(ROOT + responses[fileno]['body']) or ROOT + '/'
                        responses[fileno]['body'] = urllib.unquote(responses[fileno]['body'])

            elif event & select.EPOLLOUT:
                connections[fileno].send(get_header())

                if not bad_code[fileno] and responses[fileno]['body'] and os.path.isfile(responses[fileno]['body']) \
                        and responses[fileno]['method'] != 'HEAD':
                    my_file = open(responses[fileno]['body'], 'r')
                    try:
                        s = sendfile(connections[fileno].fileno(), my_file.fileno(), 0,
                                     os.path.getsize(responses[fileno]['body']))
                    except OSError as e:
                        if e.errno == 32:
                            # logging.exception(e.strerror)
                            pass
                    finally:
                        my_file.close()
                epoll.modify(fileno, 0)
                del responses[fileno]
                try:
                    connections[fileno].shutdown(socket.SHUT_RDWR)
                except socket.error as e:
                    if e.errno == 107:
                        # logging.exception(e.strerror)
                        pass

            elif event & select.EPOLLHUP:
                epoll.unregister(fileno)
                connections[fileno].close()
                del connections[fileno]
finally:
    # epoll_close()
    pass