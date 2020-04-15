from server import Server


def main():
    server = Server('localhost', 8000)
    try:
        server.event_loop()
    except KeyboardInterrupt:
        server.sockets[0].close()


if __name__ == '__main__':
    main()
