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

command_dc_4_point_double_stepped_i_source = {
    'cmd': 'start_measurement',
    # 'cmd': 'simulate',
    'measurement': '4point_double_stepped_i_source',
    'comment': 'S214444-20250326-RuO2 -Elias',
    'inner': 'source',  # outer will be gate
    # 'inner': 'gate',  # outer will be source
    'source': {
        'i_low': -1e-4,
        'i_high': 1e-4,
        'steps': 101,
        'repeats': 3,
        'nplc': 10,
        'limit': 0.2,
    },
    'gate': {
        'v_low': 0,
        'v_high': 0,
        'steps': 1,
        'repeats': 0,
        'nplc': 1,
        'limit': 1e-6,
    },
    'params': {'autozero': False, 'readback': False, 'source_measure_delay': 1e-3},
}


command_dc_2_point_double_stepped_v_source = {
    'cmd': 'start_measurement',
    'measurement': '2point_double_stepped_v_source',
    'comment': 'S214444-20250326-RuO2 -Elias',
    'inner': 'source',  # outer will be gate
    # 'inner': 'gate',  # outer will be source
    'source': {
        'v_low': -0.02,
        'v_high': 0.02,
        'steps': 101,
        'repeats': 2,
        'nplc': 1,
        'limit': 1e-4,
    },
    'gate': {
        'v_low': 0,
        'v_high': 0.0,
        'steps': 1,
        'repeats': 0,
        'nplc': 1,
        'limit': 1e-6,
    },
    'params': {'autozero': False, 'readback': False, 'source_measure_delay': 1e-3},
}


# command = command_toggle_6221
# command = command_dc_4_point
# command = command_delta_constant_current
# command = command_differential_conductance
# command = command_gate_sweep

# command = command_abort
# command = command_dc_2_point_double_stepped_v_source
command = command_dc_4_point_double_stepped_i_source

# time.sleep(3600)


socket_command = 'json_wn#' + json.dumps(command)
print(socket_command)
SOCK.sendto(socket_command.encode(), ('127.0.0.1', 8510))
time.sleep(0.01)
recv = SOCK.recv(65535)
print(recv)

exit()
time.sleep(1)

socket_command = 'simulation#raw'
# socket_command = 'simulation#json'
print(socket_command)
SOCK.sendto(socket_command.encode(), ('127.0.0.1', 9002))
time.sleep(0.01)
recv = SOCK.recv(65535)
print(recv)


exit()


for _ in range(0, 100):
    print()
    time.sleep(1)
    socket_command = 'status#raw'
    # socket_command = 'v_tot#raw'
    print(socket_command)
    SOCK.sendto(socket_command.encode(), ('127.0.0.1', 9002))
    time.sleep(0.01)
    recv = SOCK.recv(65535)
    print(recv)
