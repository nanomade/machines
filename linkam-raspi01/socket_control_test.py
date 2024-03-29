import time
import json
import socket

SOCK = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
SOCK.setblocking(0)

# command = {
#     'cmd': 'lock_in_frequency',
#     'frequency': 87
# }

# command = {
#     'cmd': 'abort',
# }

command = {
    'cmd': 'start_measurement',
    'measurement': 'sweeped_one_shot_vdp',
    'v_low': -20,
    'comment': 'Test - RJ',
    'v_high':20,
    'compliance': 10-4,
    'steps': 20,
    'repeats': 1,
    'time_pr_step': 0.5,
    'end_wait': 30
}

# ip of windows machine: 10.54.4.20
flow_command = 'dry: 0'
SOCK.sendto(flow_command.encode(), ('10.54.4.20', 8500))
time.sleep(0.01)
recv = SOCK.recv(65535)
print(recv)
exit()

# command = {
#     'cmd': 'start_measurement',
#     'measurement': 'constant_gate_one_shot_vdp',
#     'comment': 'Test - RJ',
#     'gate_voltage': 5,
#     'compliance': 1.1e-5,
#     'steps': 20,
#     'time_pr_step': 0.5,
#     'end_wait': 30,
#     'meas_time': 300.0,
# }

command_json = 'json_wn#' + json.dumps(command)
SOCK.sendto(command_json.encode(), ('127.0.0.1', 8500))
time.sleep(0.01)
recv = SOCK.recv(65535)
print(recv)


# for i in range(0, 20):
#     time.sleep(2)
#     SOCK.sendto('v_backgate#json'.encode(), ('127.0.0.1', 9000))
#     time.sleep(0.01)
#     recv = SOCK.recv(65535)
#     print(recv)




# command_json = 'dew_point_linkam#json'
# SOCK.sendto(command_json.encode(), ('127.0.0.1', 9001))
# time.sleep(0.01)
# recv = SOCK.recv(65535)
# print(recv)
