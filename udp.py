import socket

class Transmitter:
    PORT = 7500

    def __init__(self, ip = "127.0.0.255"):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.ip = ip

        # Allow broadcasting
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        print(f"Broadcasting to {self.ip}: {Transmitter.PORT}")

    def send(self, tagged_id):
        message = f"{tagged_id}"
        # Format is a single integer; ASCII is sufficient
        bytes = message.encode("ascii", errors = "replace") + b'\x00'
        self.sock.sendto(bytes, (self.ip, Transmitter.PORT))
        print(f"Sent: {message}")

    def close(self):
        self.sock.close()

class Receiver:
    HOST = "0.0.0.0"
    HOST_PORT = 7501
    BUFFER_SIZE = 4096

    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Allow quick restart of the program
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Bind to specified port
        self.sock.bind((Receiver.HOST, Receiver.HOST_PORT))

        print(f"Listening from {Receiver.HOST}: {Receiver.HOST_PORT}")

    def recv(self):
        bytes, addr  = self.sock.recvfrom(Receiver.BUFFER_SIZE)
        # Format is of integers and ':'; ASCII is sufficient
        message = bytes.rstrip(b'\x00').decode("ascii", errors = "replace")
        print(f"Received from {addr}: {message}")

        scored_id, sep, tagged_id = message.partition(":")

        if not sep:
            raise ValueError("Message should be formatted INTEGER:INTEGER")

        scored_id = int(scored_id)
        tagged_id = int(tagged_id)

        return (scored_id, tagged_id)

    def close(self):
        self.sock.close()
