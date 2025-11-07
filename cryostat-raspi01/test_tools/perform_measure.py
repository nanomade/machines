import time
import json
import socket

SOCK = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
SOCK.setblocking(0)


def send_b_field(command):
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


command_gate_sweep = {
    'cmd': 'start_measurement',
    'measurement': 'constant_current_gate_sweep',
    'comment': 'Mando-20250320-BR6',
    'current': 1e-7,
    'v_limit': 1,
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

command_constant_current = {
    'cmd': 'start_measurement',
    'measurement': 'constant_current',
    'comment': 'Mando-20250728-RO3',
    'current': 5e-7,
    'measure_time': 1e9,
    'v_limit': 1.0,
    'gate_v': 0,
}

command_dc_4_point = {
    'cmd': 'start_measurement',
    'measurement': 'dc_4_point',
    'comment': 'sample',
    'start': -1e-6,
    'stop': 1e-6,
    'steps': 401,
    'repeats': 3,
    'back_gate_v': 0.0,
    'v_limit': 1,
    'nplc': 10,
}

b_command = {
    'cmd': 'b_field_setpoint',
    'setpoint': 0,
    'rate': 0.15,
}

t_command = {
    'cmd': 'vti_temperature_setpoint',
    'setpoint': 0,
    'rate': 0.25,
}


for temperature in [200, 150, 100, 50, 10, 5, 1]:
    # b_start = 0
    # for b_field in [0, 10, 5, 1, 0.5, 0]:
    t_command['setpoint'] = temperature
    # send_b_field(t_command)
    # b_command['setpoint'] = b_field
    send_b_field(t_command)
    time.sleep(7200)
    # b_ramp_time = abs(60 * (b_field - b_start) / 0.15)
    # print('Ramp for {:.1f}s'.format(b_ramp_time))
    # time.sleep(b_ramp_time)
    # print('Wait for two minutes')
    # time.sleep(120)
    # b_start = b_field
    
    # wait = 20
    # for i in range(0, wait):
    #     print('Waiting for temperature stability {}/{}'.format(i, wait))
    #     time.sleep(100)

    # command = command_constant_current
    # command = command_dc_4_point
    command = command_gate_sweep
    command['comment'] = 'Camilla - T={}K'.format(temperature)
    send_meas_command(command)

    time.sleep(2000)
    
    # b_command['setpoint'] = 10
    # print('Set B 10T')
    # send_b_field(b_command)
    # time_wait = 4100
    # print('Waiting for {}s'.format(time_wait))
    # time.sleep(time_wait)

    # b_command['setpoint'] = -10
    # print('Set B -10T')
    # send_b_field(b_command)
    # time_wait = 8200
    # print('Waiting for {}s'.format(time_wait))
    # time.sleep(time_wait)

    # b_command['setpoint'] = 0
    # print('Set B 0T')
    # send_b_field(b_command)
    # time_wait = 4500
    # print('Waiting for {}s'.format(time_wait))
    # time.sleep(time_wait)

    # send_meas_command(command_abort)
    # time.sleep(1200)
    
exit()

for temperature in [0, 5, 15, 50, 100, 200, 300]:
    t_command['setpoint'] = temperature
    send_b_field(t_command)

    if temperature < 4:
        time.sleep(60)
    elif temperature < 9:
        time.sleep(3600)
    else:
        time.sleep(3 * 3600)

    for gate_v in [-15, -10, -5, 0, 5, 10, 15]:
        command = command_dc_4_point
        command['back_gate_v'] = gate_v
        msg = 'Mando-20250602-BR08 {}V, {}K'.format(gate_v, temperature)
        command['comment'] = msg
        send_meas_command(command)

        # Wait for measurement
        print('Waiting for 4200')
        time.sleep(4200)

        # # Sweep B
        # b_value = 10
        # b_command['setpoint'] = b_value
        # print('Set b-field: {}T'.format(b_value))
        # send_b_field(b_command)
        # time.sleep(4500)

        # b_value = -10
        # b_command['setpoint'] = b_value
        # print('Set b-field: {}T'.format(b_value))
        # send_b_field(b_command)
        # time.sleep(9000)

        # b_value = 0
        # b_command['setpoint'] = b_value
        # print('Set b-field: {}T'.format(b_value))
        # send_b_field(b_command)
        # time.sleep(4800)

        # # Aboort measurement
        # send_meas_command(command_abort)

        # # Wait for abort
        # print('Waiting for 1200')
        # time.sleep(1200)

# t_command['setpoint'] = 30
# send_b_field(t_command)

# b_fields = [10, 5, 1, 0]
# prev_b = 0
# for b_value in b_fields:
#     b_command['setpoint'] = b_value
#     print('Set b-field: {}T'.format(b_value))
#     send_b_field(b_command)
#     dB = abs(b_value - prev_b)
#     prev_b = b_value
#     time_wait = 60 * 5 * dB + 900
#     print('Waiting for {}s'.format(time_wait))
#     time.sleep(time_wait)

#     msg = 'Mando-20250320-BR6 - {}K - {}T'.format(temperature, b_value)
#     command = command_dc_4_point
#     command['comment'] = msg
#     send_meas_command(command)
#     print('Waiting for 800s')
#     time.sleep(800)
