import time
import json
import socket

SOCK = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
SOCK.setblocking(0)


def set_setpoint(command):
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
    'comment': 'Mando-20250320-BR6',
    'current': 5e-8,
    'measure_time': 1e9,
    'v_limit': 1.0,
    'gate_v': 0,
}


command_dc_4_point = {
    'cmd': 'start_measurement',
    'measurement': 'dc_4_point',
    'comment': 'Elias: WTe2 - thin - 300K',
    'start': -1e-7,
    'stop': 1e-7,
    'steps': 201,
    'repeats': 3,
    'back_gate_v': 0.0,
    'v_limit': 10.0,
    'nplc': 10,
}


t_command = {
    'cmd': 'vti_temperature_setpoint',
    'setpoint': 5,
    'rate': 2.0,
}

b_command = {
    'cmd': 'b_field_setpoint',
    'setpoint': 0,
    'rate': 0.15,
}


for T in [15, 50, 100]:

    t_command['setpoint'] = T
    set_setpoint(t_command)
    time.sleep((T-15) * 60)    

    for current in [1e-6, 5e-7, 1e-7, 1e-8, 5e-9]:
        comment = 'Mando-20250320-BR6: {:.0f}nA, {:.0f}K'.format(current*1e9, T)
        print(comment)
        command_constant_current['comment'] = comment
        command_constant_current['current'] = current
        send_meas_command(command_constant_current)

        time.sleep(600)

        b_command['setpoint'] = 11.99
        print('Set b-field: {}T'.format(11.99))
        set_setpoint(b_command)
        time.sleep(7 * 12 * 60)

        b_command['setpoint'] = -11.99
        print('Set b-field: {}T'.format(-11.99))
        set_setpoint(b_command)
        time.sleep(7 * 24 * 60)

        b_command['setpoint'] = 0
        print('Set b-field: {}T'.format(0))
        set_setpoint(b_command)
        time.sleep(7 * 12 * 60)

        send_meas_command(command_abort)
        
        time.sleep(600)

exit()
# ******************

command_constant_current['current'] = 5e-9
send_meas_command(command_constant_current)

time.sleep(600)

b_command['setpoint'] = 11.99
print('Set b-field: {}T'.format(11.99))
set_setpoint(b_command)
time.sleep(7 * 12 * 60)

b_command['setpoint'] = -11.99
print('Set b-field: {}T'.format(-11.99))
set_setpoint(b_command)
time.sleep(7 * 24 * 60)

b_command['setpoint'] = 0
print('Set b-field: {}T'.format(0))
set_setpoint(b_command)
time.sleep(7 * 12 * 60)

send_meas_command(command_abort)



exit()
temperatures = [4, 10, 100, 200, 300]

for temperature in temperatures:

    t_command['setpoint'] = temperature
    set_setpoint(t_command)
    if temperature < 5:
        time.sleep(6)
    elif temperature < 100:
        time.sleep(600)
    else:
        time.sleep(3600)

    b_command['setpoint'] = 11.99
    print('Set b-field: {}T'.format(11.99))
    set_setpoint(b_command)
    time_wait = 60 * 4 * 12 + 300
    print('Waiting for {}s'.format(time_wait))
    time.sleep(time_wait)

    b_command['setpoint'] = -11.99
    print('Set b-field: {}T'.format(-11.99))
    set_setpoint(b_command)
    time_wait = 60 * 4 * 24 + 300
    print('Waiting for {}s'.format(time_wait))
    time.sleep(time_wait)

    b_command['setpoint'] = 11.99
    print('Set b-field: {}T'.format(11.99))
    set_setpoint(b_command)
    time_wait = 60 * 4 * 24 + 300
    print('Waiting for {}s'.format(time_wait))
    time.sleep(time_wait)


    b_command['setpoint'] = 0
    print('Set b-field: {}T'.format(0))
    set_setpoint(b_command)
    time_wait = 60 * 4 * 12 + 300
    print('Waiting for {}s'.format(time_wait))
    time.sleep(time_wait)




send_meas_command(command_abort)
