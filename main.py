from .server import Server


def main():
    server = Server('localhost', 8090)
    try:
        server.event_loop()
    except KeyboardInterrupt:
        server.server_sock.close()


if __name__ == '__main__':
    main()
