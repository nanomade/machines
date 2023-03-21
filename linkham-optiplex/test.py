import time
import json
import socket

SOCK = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
SOCK.setblocking(0)

command = {
    'cmd': 'set_flow',
    'device': 'dry',
    'value': 0
}

socket_command = 'json_wn#' + json.dumps(command)
print(socket_command)
exit()
SOCK.sendto(socket_command.encode(), ('127.0.0.1', 8500))
time.sleep(0.01)
recv = SOCK.recv(65535)
print(recv)

exit()

for i in range(0, 20):
    time.sleep(2)
    # cmd = 'mfc_flow_dry_setpoint_linkham#json'
    cmd = 'mfc_flow_dry_linkham#json'
    SOCK.sendto(cmd.encode(), ('127.0.0.1', 9000))
    time.sleep(0.01)
    recv = SOCK.recv(65535)
    print(recv)
