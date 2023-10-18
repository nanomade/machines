import time
import json
import socket

SOCK = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
SOCK.setblocking(0)

# command = {
#         'cmd': 'abort',
#     }

command = {
    'cmd': 'start_measurement',
    # 'measurement': 'record_noise_spectrum',
    'measurement': 'record_xy_spectrum',
    # 'measurement': 'record_sweeped_xy_measurement',
    'acquisition_time': 15,
    'comment': 'Test',
    'freq_high': 1e5,
    'freq_low': 100,
    'steps': 8,
}


socket_command = 'json_wn#' + json.dumps(command)
print(socket_command)
SOCK.sendto(socket_command.encode(), ('127.0.0.1', 8500))
time.sleep(0.01)
recv = SOCK.recv(65535)
print(recv)


# socket_command = 'measurement_running#json'
# print(socket_command)
# SOCK.sendto(socket_command.encode(), ('127.0.0.1', 9000))
# time.sleep(0.01)
# recv = SOCK.recv(65535)
# print(recv)

