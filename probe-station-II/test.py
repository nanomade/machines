import time
import json
import socket

SOCK = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
SOCK.setblocking(0)


command_abort = {
    'cmd': 'abort',
}



# command_gate_sweep = {
#     'cmd': 'start_measurement',
#     'measurement': 'constant_current_gate_sweep',
#     'comment': 'Test',
#     'current': 80e-9,
#     'v_limit': 2,
#     'v_low': -2,
#     'v_high': 2,
#     'steps': 101,
#     'repeats': 3,
#     'nplc': 10,
# }

# command_dc_4_point = {
#     'cmd': 'start_measurement',
#     'measurement': 'dc_4_point',
#     'comment': 'Test',
#     'start': -2e-9,
#     'stop': 2e-9,
#     'steps': 201,
#     'gate_v': 0.987654,
#     'v_limit': 2,
#     'nplc': 10,
# }

# command_delta_constant_current = {
#     'cmd': 'start_measurement',
#     'measurement': 'delta_constant_current',
#     'comment': 'Test',
#     'current': 10e-9,
#     'measure_time': 60,
#     'v_limit': 1.1,
#     'gate_v': 1.12,
# }

# command_differential_conductance = {
#     'cmd': 'start_measurement',
#     'measurement': 'diff_conductance',
#     'comment': 'Test',
#     'start': 1.1e-7,
#     'stop': 1e-4,
#     'steps': 1000,
#     'delta': 1.1e-7,
#     'v_limit': 4.1,
#     'gate_v': 1.75
# }


command_dc_4_double_stepped = {
    'cmd': 'start_measurement',
    'measurement': '4point_double_stepped',
    'comment': 'network test - double stepped',
    'inner': 'source',  # outer will be gate
    # inner='gate',  # outer will be source
    # NPLC?
    'source': {'start': -0.2, 'stop': 0.2, 'steps': 50, 'limit': 2e-3},
    'gate': {'start': -5.0, 'stop': 5.0, 'steps': 3, 'limit': 1e-7},
}


# command = command_toggle_6221
# command = command_dc_4_point
# command = command_delta_constant_current
# command = command_differential_conductance
# command = command_gate_sweep

command = command_abort
# command = command_dc_4_double_stepped

socket_command = 'json_wn#' + json.dumps(command)
print(socket_command)
SOCK.sendto(socket_command.encode(), ('127.0.0.1', 8510))
time.sleep(0.01)
recv = SOCK.recv(65535)
print(recv)
