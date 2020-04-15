import json
import time
from select import select
from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR

from utils import is_in


class Server:
    http_response = b"HTTP/1.1 200 OK"
    CONN_TIMEOUT = 0.001
    SOCK_TIMEOUT = 0.001

    def __init__(
            self,
            host: str,
            port: int,

    ):
        self.config = {}

        self.host = host
        self.port = port

        self.server_sock = socket(AF_INET, SOCK_STREAM)
        self.server_sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.server_sock.bind((host, port))
        self.server_sock.listen()

        self.connection_generators = []
        self.upload_conf()

    def event_loop(self):
        while True:
            ready_to_read, _, _ = select([self.server_sock], [], [], self.SOCK_TIMEOUT)

            if ready_to_read:
                self.create_connection()

            for conn_gen in self.connection_generators:
                try:
                    conn_gen.__next__().decode()
                except StopIteration:
                    self.connection_generators.remove(conn_gen)

    @staticmethod
    def parse_http_request(request: bytes) -> dict:
        request = request.decode().split('\r\n\r\n')[0]

        http_lines = request.split("\n")
        method, url, protocol = http_lines[0].split(' ')
        headers = {}
        for i in range(1, len(http_lines)):
            key = http_lines[i].split(": ")[0]
            value = http_lines[i].split(" ")[1]
            headers[key] = value

        return {
            'method': method,
            'url': url,
            'protocol': protocol,
            'headers': headers
        }

    def create_conn_generator(self):
        conn, addr = self.server_sock.accept()
        request_param = {}

        ready_to_read, ready_to_write, _ = select([conn], [], [], self.CONN_TIMEOUT)
        r = b''

        while ready_to_read:
            request_chunk = conn.recv(4096)
            r += request_chunk

            if not request_param:
                request_param = self.parse_http_request(request_chunk)
            yield request_chunk
            ready_to_read, _, _ = select([conn], [], [], self.CONN_TIMEOUT)

        print(r.decode())
        if request_param:
            if request_param["url"] == '/':
                conn.sendall(self.http_response + b'\n\n' + b'hello')
            else:
                file_content = self.get_file_content(request_param["url"])
                conn.sendall(self.http_response + b'\n\n' + file_content)

        conn.close()

    def create_connection(self):
        self.connection_generators.append(self.create_conn_generator())

    def upload_conf(self):
        with open('server_conf.json') as conf:
            self.config = json.load(conf)

    def get_file_content(self, file_path: str) -> bytes:
        file_content: bytes
        with open(self.config['server']['static'] + file_path, mode='rb') as file:
            file_content = file.read()

        return file_content
