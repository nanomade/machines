import time
import json
import socket

SOCK = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
SOCK.setblocking(0)


def send(cmd):
    socket_command = 'json_wn#' + json.dumps(command)
    print(socket_command)
    SOCK.sendto(socket_command.encode(), ('127.0.0.1', 8500))
    time.sleep(0.01)
    recv = SOCK.recv(65535)
    print(recv)


command = {
    'cmd': 'vti_setpoint',
    'setpoint': 2,
}
# time.sleep(2500)
send(command)
exit()
for s in range(80, 20, -1):
    command['setpoint'] = s / 10.0
    send(command)
    time.sleep(80)

# exit()
