import time

import json
import socket
import network
import machine

def blink(t):
    led.value(not led.value())

def led_show_ok():
    led.value(1)
    time.sleep(0.5)
    led.value(0)

def B_field(voltage):
    r1 = 100
    B = voltage / (4 * 12.2 * r1)
    return B

def read_voltage_diff():
    v_list = []
    for i in range(0, 500):
        v1 = adc1.read_uv()
        v2 = adc2.read_uv()
        v_list.append(v1 - v2)
    v_out = (sum(v_list) / len(v_list)) / 1e6
    return v_out

LOCATION = '309_926'
timer = machine.Timer(1)

led = machine.Pin(2, machine.Pin.OUT)
timer.init(period=100, mode=machine.Timer.PERIODIC, callback=blink)

# Connect to network
print('Connect to wifi')
sta_if = network.WLAN(network.STA_IF)
sta_if.active(True)

print('Connecting...')
sta_if.connect('device')
time.sleep(5)
ifconfig = sta_if.ifconfig()
ip_addr = ifconfig[0]
print('ip: {}'.format(ip_addr))

time.sleep(2.5)

udpsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udpsocket.connect(('', 8500))

adc1 = machine.ADC(machine.Pin(36))
adc1.atten(machine.ADC.ATTN_11DB)
adc2 = machine.ADC(machine.Pin(34))
adc2.atten(machine.ADC.ATTN_11DB)

while True:
    time.sleep(1)
    ifconfig = sta_if.ifconfig()
    ip_addr = ifconfig[0]
    connected = sta_if.isconnected()
    print('Connected', connected)
    if not connected:
        timer.init(period=100, mode=machine.Timer.PERIODIC, callback=blink)
        print('Not connected to wifi -  try again')
        sta_if.disconnect()
        time.sleep(2)
        sta_if.connect('device')
        time.sleep(5)
        continue
    timer.deinit()
    timer.init(period=2000, mode=machine.Timer.PERIODIC, callback=blink)

    # v_high = adc1.read_uv() / 1e6
    # v_low = adc2.read_uv() / 1e6
    # v_out = v_high - v_low
    v_out = read_voltage_diff()
    B = B_field(v_out)
    msg = 'Voltage is: {:.1f}mV. B-field is {:.1f}uT'
    print(msg.format(v_out * 1000, B * 1e6))

    data = {
       'location': LOCATION,
       'b_field': B,
    }
    udp_string = 'json_wn#' + json.dumps(data)
    print(udp_string, ip_addr)
    try:
        udpsocket.sendto(udp_string, ('10.199.253.148', 8500))
        led_show_ok()
    except OSError:
        print('Did not manage to send udp')
    print()
