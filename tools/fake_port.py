# fake_port.py
import socket
import argparse

parser = argparse.ArgumentParser(description="Run a fake port listener.")
parser.add_argument("--port", type=int, required=True, help="Port number to listen on")
args = parser.parse_args()

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(('127.0.0.1', args.port))
server_socket.listen(5)

print(f"[+] Listening on port {args.port}...")

try:
    while True:
        client_socket, addr = server_socket.accept()
        print(f"[!] Connection from {addr}")
        client_socket.sendall(b"Fake service response\n")
        client_socket.close()
except KeyboardInterrupt:
    print("\n[-] Shutting down.")
    server_socket.close()
