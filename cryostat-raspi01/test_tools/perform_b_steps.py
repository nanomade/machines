import time
import json
import socket

SOCK = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
SOCK.setblocking(0)


def send_setpoint(command):
    socket_command = 'json_wn#' + json.dumps(command)
    print(socket_command)
    SOCK.sendto(socket_command.encode(), ('127.0.0.1', 8500))
    time.sleep(0.01)
    recv = SOCK.recv(65535)
    print(recv)


def send_meas_command(command):
    socket_command = 'json_wn#' + json.dumps(command)
    print(socket_command)
    SOCK.sendto(socket_command.encode(), ('127.0.0.1', 8510))
    time.sleep(0.01)
    recv = SOCK.recv(65535)
    print(recv)


command_abort = {
    'cmd': 'abort',
}

command_constant_current = {
    'cmd': 'start_measurement',
    'measurement': 'constant_current',
    'comment': 'Elias: WTe2 - thin - B-sweep',
    'current': 5e-8,
    'measure_time': 1e9,
    'v_limit': 10.0,
    'gate_v': 0,
}


command_dc_4_point = {
    'cmd': 'start_measurement',
    'measurement': 'dc_4_point',
    'comment': 'Elias: WTe2 - thin - 100K',
    'start': -1e-7,
    'stop': 1e-7,
    'steps': 201,
    'repeats': 3,
    'back_gate_v': 0.0,
    'v_limit': 10.0,
    'nplc': 10,
}

b_command = {
    'cmd': 'b_field_setpoint',
    'setpoint': 0,
    'rate': 0.25,
}


send_meas_command(command_constant_current)

time.sleep(120)

b_command['setpoint'] = 10
print('Set B: 10T')
send_setpoint(b_command)
time_wait = (60 * 10 * 4) + 600
print('Waiting for {}s'.format(time_wait))
time.sleep(time_wait)

b_command['setpoint'] = -10
print('Set B: -10T')
send_setpoint(b_command)
time_wait = (60 * 20 * 4) + 600
print('Waiting for {}s'.format(time_wait))
time.sleep(time_wait)

b_command['setpoint'] = 10
print('Set B: 10T')
send_setpoint(b_command)
time_wait = (60 * 20 * 4) + 600
print('Waiting for {}s'.format(time_wait))
time.sleep(time_wait)

b_command['setpoint'] = -10
print('Set B: -10T')
send_setpoint(b_command)
time_wait = (60 * 20 * 4) + 600
print('Waiting for {}s'.format(time_wait))
time.sleep(time_wait)

b_command['setpoint'] = 10
print('Set B: 10T')
send_setpoint(b_command)
time_wait = (60 * 20 * 4) + 600
print('Waiting for {}s'.format(time_wait))
time.sleep(time_wait)

b_command['setpoint'] = -10
print('Set B: -10T')
send_setpoint(b_command)
time_wait = (60 * 20 * 4) + 600
print('Waiting for {}s'.format(time_wait))
time.sleep(time_wait)


b_command['setpoint'] = 0
print('Set B: 0T')
send_setpoint(b_command)
time_wait = (60 * 10 * 4) + 600
print('Waiting for {}s'.format(time_wait))
time.sleep(time_wait)


# send_meas_command(command_abort)
