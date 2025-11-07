import time
import json
import socket

SOCK = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
SOCK.setblocking(0)


command_abort = {
    'cmd': 'abort',
}

command_toggle_6221 = {
    'cmd': 'toggle_6221',
}


command_gate_sweep = {
    'cmd': 'start_measurement',
    'measurement': 'constant_current_gate_sweep',
    'comment': 'Mando-2025-09-25-RO7 - 300K',
    'current': 1e-7,
    'v_limit': 1.0,
    'nplc': 5,
    'back_gate': {
        'v_low': -15.0,
        'v_high': 15.0,
        'steps': 401,
        'repeats': 3,
    },
    'front_gate': None,
    # 'front_gate': {
    #    'v_low': -5.0,
    #    'v_high': 5.0,
    #    'steps': 15,
    #},
}

command_delta_gate_sweep = {
    'cmd': 'start_measurement',
    'measurement': 'delta_constant_current_gate_sweep', 
    'comment': 'Started froom test.py',
    'current': 5e-8,
    'v_limit': 5,
    'v_low': -3,
    'v_high': 2,
    'steps': 501,
    'repeats': 3,
    'nplc': 5,
    'v_xx_range': 2
}

command_delta_constant_current = {
    'cmd': 'start_measurement',
    'measurement': 'delta_constant_current',
    'comment': 'Test sample',
    'current': 2e-5,
    'measure_time': 1e7,
    'v_limit': 10.0,
    'gate_v': 0.0,
}

command_constant_current = {
    'cmd': 'start_measurement',
    'measurement': 'constant_current',
    'comment': 'Mando-2025-09-25-RO7 - Cooldown',
    'current': 1e-7,
    'measure_time': 1e9,
    'v_limit': 1.0,
    'gate_v': 0,
}

command_differential_conductance = {
    'cmd': 'start_measurement',
    'measurement': 'diff_conductance',
    'comment': 'Test',
    'start': 1.1e-7,
    'stop': 1e-4,
    'steps': 1000,
    'delta': 1.1e-6,
    'v_limit': 4.1,
    'gate_v': 1.75
}

command_dc_4_point = {
    'cmd': 'start_measurement',
    'measurement': 'dc_4_point',
    'comment': 'Mando-2025-09-25-RO7 - 300k',
    'start': -1e-6,
    'stop': 1e-6,
    'steps': 401,
    'repeats': 3,
    'back_gate_v': 0.0,
    'v_limit': 1,
    'nplc': 5,
}


# command = command_toggle_6221
# command = command_dc_4_point
# command = command_delta_constant_current
# command = command_delta_gate_sweep 
# command = command_differential_conductance
command = command_gate_sweep
# command = command_dc_4_point
# command = command_constant_current
command = command_abort
# time.sleep(3600)
socket_command = 'json_wn#' + json.dumps(command)
print(socket_command)
SOCK.sendto(socket_command.encode(), ('127.0.0.1', 8510))
time.sleep(0.01)
recv = SOCK.recv(65535)
print(recv)

exit()
time.sleep(2600)

command['back_gate_v'] = -15.0
command['comment'] = 'Choso-20250912-MoWT - Subdevice 2 - -15V - 275K',
socket_command = 'json_wn#' + json.dumps(command)
print(socket_command)
SOCK.sendto(socket_command.encode(), ('127.0.0.1', 8510))
time.sleep(0.01)
recv = SOCK.recv(65535)
print(recv)


exit()

