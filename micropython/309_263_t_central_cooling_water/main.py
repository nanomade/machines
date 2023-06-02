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
    
def init_wlan():
    print('Connect to network')
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect('device')
    time.sleep(5)
    ifconfig = wlan.ifconfig()
    ip_addr = ifconfig[0]
    print('ip: {}'.format(ip_addr))
    return wlan
    
def read_temperature(adc, avg=500):
    avg_sum = 0
    for i in range(0, avg):
        avg_sum += adc.read_uv()
    temperature = 1.0 * avg_sum / (avg * 1e4)
    return temperature
    
LOCATION = '309_263'
timer = machine.Timer(1)

led = machine.Pin(2, machine.Pin.OUT)
timer.init(period=100, mode=machine.Timer.PERIODIC, callback=blink)

wlan = init_wlan()

udpsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udpsocket.connect(('', 8500))

adc_cold = machine.ADC(machine.Pin(36))  # Blue
adc_cold.atten(machine.ADC.ATTN_0DB)  # Default, not really needed
adc_hot = machine.ADC(machine.Pin(34))  # Brown
adc_hot.atten(machine.ADC.ATTN_0DB)  # Default, not really needed

# print(read_temperature(adc_cold), read_temperature(adc_hot))


while True:
    time.sleep(2)
    connected = wlan.isconnected()
    print('Connected', connected)
    if not connected:
        timer.init(period=100, mode=machine.Timer.PERIODIC, callback=blink)
        print('Not connected to wifi -  try again')
        wlan.disconnect()
        time.sleep(2)
        wlan.connect('device')
        time.sleep(5)
        continue
    timer.deinit()
    timer.init(period=2000, mode=machine.Timer.PERIODIC, callback=blink)

    t_cold = read_temperature(adc_cold)
    t_hot = read_temperature(adc_hot)
    msg = 'T-hot: {:.2f}C. T-cold {:.2f}C'
    print(msg.format(t_hot, t_cold))

    data = {
        'location': LOCATION,
        't_central_cooling_water_forward': t_cold,
        't_central_cooling_water_return': t_hot,
    }
    udp_string = 'json_wn#' + json.dumps(data)
    print(udp_string)
    try:
        udpsocket.sendto(udp_string, ('10.199.253.148', 8500))
        led_show_ok()
    except OSError:
        print('Did not manage to send udp')
    print()

