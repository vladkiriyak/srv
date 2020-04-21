import json
import time
from select import select
from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
from typing import Optional, Generator


class Request:

    def __init__(self, raw_request: bytes):
        raw_http_title, body = raw_request.decode().split('\r\n\r\n')

        http_lines = raw_http_title.split("\n")
        method, url, protocol = http_lines[0].split(' ')
        headers = {}
        for i in range(1, len(http_lines)):
            key = http_lines[i].split(": ")[0]
            value = http_lines[i].split(" ")[1]
            headers[key] = value

        self.__method = method
        self.__url = url
        self.__protocol = protocol
        self.__headers = headers
        self.__body = body

    @property
    def body(self):
        return self.__body

    @property
    def method(self):
        return self.__method

    @property
    def url(self):
        return self.__url

    @property
    def protocol(self):
        return self.__protocol

    @property
    def headers(self):
        return self.__headers


class Server:
    http_request = b'GET / HTTP/1.1'
    http_response = b"HTTP/1.1 200 OK"

    CONN_TIMEOUT = 0
    SOCK_TIMEOUT = 0
    ASYNC_TIMEOUT = 1000

    def __init__(
            self,
            host: str,
            port: int,

    ):
        self.config = {}

        self.host = host
        self.port = port
        self.upload_conf()

        self.server_sock = socket(AF_INET, SOCK_STREAM)
        self.server_sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.server_sock.bind((host, port))
        self.server_sock.listen()

        self.balancing_generator = self.create_balancing_generator()
        self.connection_generators = []

    def create_balancing_generator(self):
        while True:
            for hosting in self.config['load_balancer']['urls']:
                yield hosting

    def event_loop(self):
        while True:

            ready_to_read, _, e = select([self.server_sock], [], [], self.SOCK_TIMEOUT)

            if ready_to_read:
                self.create_connection()

            conn_gen = 0
            while conn_gen < len(self.connection_generators):
                try:
                    self.connection_generators[conn_gen].__next__()
                except StopIteration:
                    self.connection_generators.remove(self.connection_generators[conn_gen])
                conn_gen += 1

    def create_async_connection(self):
        conn, addr = self.server_sock.accept()
        request: Optional[Request] = None

        raw_data = yield from self.async_recv(conn, self.ASYNC_TIMEOUT, self.CONN_TIMEOUT, False)
        if not raw_data:
            return
        request = Request(raw_data)

        if request.url == '/':
            conn.sendall(self.http_response + b'\n\n' + b'hello')
        elif request.url == '/loadMethod':

            sock = socket(AF_INET, SOCK_STREAM)
            sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

            sock.connect(tuple(self.balancing_generator.__next__()))
            sock.sendall(self.http_request + b'\n\n')
            raw_response = yield from self.async_recv(sock, self.ASYNC_TIMEOUT, self.CONN_TIMEOUT, True)
            if not raw_response:
                return

            conn.sendall(raw_response)

        else:
            file_content = self.get_file_content(request.url)
            conn.sendall(self.http_response + b'\n\n' + file_content)

        conn.close()

    @staticmethod
    def async_recv(conn, async_timeout, conn_timeout, is_steam: bool):

        raw_data = b''
        _async_timeout = async_timeout
        ready_to_read, ready_to_write, _ = select([conn], [], [], conn_timeout)
        while True:

            if _async_timeout == 0:
                break

            if not ready_to_read:
                _async_timeout -= 1
                yield
                ready_to_read, ready_to_write, _ = select([conn], [], [], conn_timeout)
                continue

            _async_timeout = async_timeout
            request_chunk = conn.recv(4096)

            if not request_chunk:
                break

            raw_data += request_chunk
            if not is_steam:
                break
            yield
            ready_to_read, _, _ = select([conn], [], [], conn_timeout)

        return raw_data

    def create_connection(self):
        self.connection_generators.append(self.create_async_connection())

    def upload_conf(self):
        with open('server_conf.json') as conf:
            self.config = json.load(conf)

    def get_file_content(self, file_path: str) -> bytes:
        file_content: bytes
        try:
            with open(self.config['server']['static'] + file_path, mode='rb') as file:
                file_content = file.read()
        except (IsADirectoryError, FileNotFoundError):
            with open(self.config['server']['static'] + '/page_not_found.html', mode='rb') as file:
                file_content = file.read()

        return file_content
