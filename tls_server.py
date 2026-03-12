import socket
import ssl

HOST="0.0.0.0"
PORT=8000

context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain("server.crt","server.key")

sock=socket.socket()
sock.bind((HOST,PORT))
sock.listen()

secure=context.wrap_socket(sock,server_side=True)

print("TLS control server running")

while True:

    conn,addr=secure.accept()

    print("client authenticated:",addr)

    conn.send(b"AUTH_OK")

    conn.close()