import socket
import threading
import argparse

parser = argparse.ArgumentParser(description='Argument Parser')
parser.add_argument('--num', help='Number of concurrent mice flows', default=10, type=int)

def client(ip, port, message):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((ip, port))
    try:
        sock.sendall(message)
        time.sleep(2)
        sock.sendall(message)
        response = sock.recv(1024)
        print "Received: {}".format(response)
    finally:
        sock.close()

if __name__ == "__main__":

    args = parser.parse_args()

    ip, port = "192.168.0.2", 9999

    while (1):
        if threading.active_count() < args.num:
            threading.Thread(target=client, args=(ip, port, "Hello World",)).start()
