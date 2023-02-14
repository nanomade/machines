import time
import json
import socket

SOCK = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
SOCK.setblocking(0)

command = {
    'cmd': 'lock_in_frequency',
    'frequency': 87
}

command = {
    'cmd': 'start_measurement',
    'measurement': 'one_shot_vdp',
    'v_low': -20,
    'comment': 'Test - RJ',
    'v_high':20,
    'compliance': 10-4,
    'total_steps': 20,
    'repeats': 1,
    'time_pr_step': 0.2,
    'end_wait': 0
}

command_json = 'json_wn#' + json.dumps(command)
print(command_json)

SOCK.sendto(command_json.encode(), ('127.0.0.1', 8500))
time.sleep(0.01)
recv = SOCK.recv(65535)
print(recv)

for i in range(0, 20):
    time.sleep(2)
    SOCK.sendto('v_backgate#json'.encode(), ('127.0.0.1', 9000))
    time.sleep(0.01)
    recv = SOCK.recv(65535)
    print(recv)

