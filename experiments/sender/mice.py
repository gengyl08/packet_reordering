import socket
import threading
import SocketServer
import time

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

    ip, port = "192.168.0.2", 9999

    t0 = threading.Thread(target=client, args=(ip, port, "Hello World 0",))
    t1 = threading.Thread(target=client, args=(ip, port, "Hello World 1",))

    t0.start()
    t1.start()

    t0.join()
    t1.join()