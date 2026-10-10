import select
import socket
import sys

def forward(src, dst):
    while True:
        r, w, x = select.select([src, dst], [], [])
        if src in r:
            data = src.recv(4096)
            if not data:
                break
            dst.sendall(data)
        if dst in r:
            data = dst.recv(4096)
            if not data:
                break
            src.sendall(data)

def main():
    listen_ip = sys.argv[1] if len(sys.argv) > 1 else "0.0.0.0"
    listen_port = int(sys.argv[2]) if len(sys.argv) > 2 else 11435
    target_ip = sys.argv[3] if len(sys.argv) > 3 else "127.0.0.1"
    target_port = int(sys.argv[4]) if len(sys.argv) > 4 else 11434

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((listen_ip, listen_port))
    server.listen(10)
    print(f"Forwarding {listen_ip}:{listen_port} -> {target_ip}:{target_port}")

    while True:
        client_sock, addr = server.accept()
        try:
            target_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            target_sock.connect((target_ip, target_port))
            import threading
            t = threading.Thread(target=forward, args=(client_sock, target_sock), daemon=True)
            t.start()
        except Exception as e:
            print("Error forwarding connection:", e)
            client_sock.close()

if __name__ == "__main__":
    main()
