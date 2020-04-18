import json
import time
from select import select
from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
from typing import Optional, Generator


class Request:

    def __init__(self, request: bytes):
        request = request.decode().split('\r\n\r\n')[0]
        http_lines = request.split("\n")
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
    ASYNC_TIMEOUT = 100000

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
            ready_to_read, _, _ = select([self.server_sock], [], [], self.SOCK_TIMEOUT)

            if ready_to_read:
                self.create_connection()

            for conn_gen in self.connection_generators:
                try:
                    conn_gen.__next__()
                except StopIteration:
                    self.connection_generators.remove(conn_gen)

    def create_conn_generator(self):
        conn, addr = self.server_sock.accept()
        request: Optional[Request] = None

        ready_to_read, ready_to_write, _ = select([conn], [], [], self.CONN_TIMEOUT)
        timeout = self.ASYNC_TIMEOUT
        while not ready_to_read and timeout != 0:
            ready_to_read, ready_to_write, _ = select([conn], [], [], self.CONN_TIMEOUT)
            timeout -= 1
            yield

        raw_request = b''

        while ready_to_read:
            request_chunk = conn.recv(4096)
            raw_request += request_chunk

            if not request_chunk:
                break

            if not request:
                request = Request(request_chunk)

            yield request_chunk
            ready_to_read, _, _ = select([conn], [], [], self.CONN_TIMEOUT)

        if request:
            if request.url == '/':
                conn.sendall(self.http_response + b'\n\n' + b'hello')
            elif request.url == '/loadMethod':

                sock = socket(AF_INET, SOCK_STREAM)
                sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

                sock.connect(tuple(self.balancing_generator.__next__()))
                sock.sendall(self.http_request + b'\n\n')

                raw_response = self.recv_all(sock, 0.01)

                conn.sendall(raw_response)


            else:
                file_content = self.get_file_content(request.url)
                conn.sendall(self.http_response + b'\n\n' + file_content)

        conn.close()

    @staticmethod
    def recv_all(sock: socket, timeput: float) -> bytes:
        raw_response = b''
        ready_to_read, _, _ = select([sock], [], [], timeput)
        while ready_to_read:
            request_chunk = sock.recv(4096)
            raw_response += request_chunk

            if not request_chunk:
                break

            ready_to_read, _, _ = select([sock], [], [], timeput)

        sock.close()
        return raw_response

    def create_connection(self):
        self.connection_generators.append(self.create_conn_generator())

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
