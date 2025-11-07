import time
import json
import socket

SOCK = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
SOCK.setblocking(0)


def send(cmd):
    socket_command = 'json_wn#' + json.dumps(command)
    print(socket_command)
    SOCK.sendto(socket_command.encode(), ('127.0.0.1', 8500))
    time.sleep(0.01)
    recv = SOCK.recv(65535)
    print(recv)

command = {
    # 'cmd': 'sample_temperature_setpoint',
    'cmd': 'vti_temperature_setpoint',
    # 'cmd': 'b_field_setpoint',
    'setpoint': 1,
    'rate': 0.25 # T/min or K/min
}
send(command)
exit()
time.sleep(100)
for t_raw in range(1710, 3000, 1):
    setpoint = t_raw / 10
    command['setpoint'] =  setpoint
    send(command)
    time.sleep(10)

time.sleep(1200)
    
setpoint = 1
send(command)

    
exit()
rate = 0.25 
time.sleep(600)
command['rate'] = rate
command['setpoint'] = 10
send(command)
dt = 10 * 60 / rate
time.sleep(dt + 10)

command['setpoint'] = -10
send(command)
dt = 20 * 60 / rate
time.sleep(dt + 20)

command['setpoint'] = 0
send(command)

dt = 10 * 60 / rate
time.sleep(dt + 500)

exit()
time.sleep(1200)
for T in range(16, 1200):
    t = T * 0.25
    command['setpoint'] = t
    send(command)
    time.sleep(30)

command['setpoint'] = 5
send(command)
exit()
# for t in [50, 100, 150, 200, 250, 300]:
for t in [300]:
    command['cmd'] = 'b_field_setpoint'
    command['setpoint'] = 11.99
    send(command)
    time.sleep(5 * 13 * 60)

    command['setpoint'] = -11.99
    send(command)
    time.sleep(5 * 26 * 60)

    command['setpoint'] = 0
    send(command)
    time.sleep(5 * 13 * 60)

    command['cmd'] = 'vti_temperature_setpoint'
    command['setpoint'] = t
    send(command)
    time.sleep(7200)

exit()

command['setpoint'] = 0
send(command)
time.sleep(5000)

command = {
    # 'cmd': 'sample_temperature_setpoint',
    'cmd': 'vti_temperature_setpoint',
    # 'cmd': 'b_field_setpoint',
    'setpoint': 300,
    'rate': 0.25 # T/min or K/min
}
send(command)



exit()
time.sleep(5200)

command = {
    # 'cmd': 'sample_temperature_setpoint',
    # 'cmd': 'vti_temperature_setpoint',
    'cmd': 'b_field_setpoint',
    'setpoint': 11.95,
    'rate': 0.25 # T/min or K/min
}
send(command)
time.sleep(4000)

command['setpoint'] = -11.96
send(command)
time.sleep(8000)

command['setpoint'] = 0
send(command)


exit()
for temp in [50, 30, 20, 10, 7, 100, 200, 280]:
    time.sleep(7200)
    command['setpoint'] = temp
    send(command)

exit()

time.sleep(7200)

for i in range(3, 300, 1):
    command['setpoint'] = i
    send(command)
    time.sleep(45)


time.sleep(600)

for i in range(300, 3, -1):
    command['setpoint'] = i
    send(command)
    time.sleep(45)

exit()

time.sleep(4000)

command['setpoint'] = 11.9
send(command)
time.sleep(8000)

command['setpoint'] = 0
send(command)
