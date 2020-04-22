from .http import HTTP_CODE
from .interfaces import HTTPObject


class Response(HTTPObject):
    def __init__(self, raw_http_head: bytes):
        self.raw_http_head = raw_http_head

        http_head = raw_http_head.decode()

        http_lines = http_head.split("\n")
        protocol, code, status = http_lines[0].split(' ')
        headers = {}
        for i in range(1, len(http_lines)):
            key = http_lines[i].split(": ")[0]
            value = http_lines[i].split(" ")[1]
            headers[key] = value

        self.__code: HTTP_CODE = code
        self.__status = status
        self.__protocol = protocol
        self.__headers: dict = headers
        self.body = ''

    @property
    def raw(self):
        return self.raw_http_head + b'\r\n\r\n' + self.body.encode()

    @property
    def code(self):
        return self.__code

    @property
    def status(self):
        return self.__status

    @property
    def protocol(self):
        return self.__protocol

    @property
    def headers(self) -> dict:
        return self.__headers


class Request(HTTPObject):

    def __init__(self, raw_http_head: bytes):
        self.raw_http_head = raw_http_head
        http_head = raw_http_head.decode()

        http_lines = http_head.split("\n")
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
        self.body = ''

    @property
    def raw(self):
        return self.raw_http_head + b'\r\n\r\n' + self.body.encode()

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
