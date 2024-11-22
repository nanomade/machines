import time
import json
import network
import socket
import machine
from machine import Pin, Timer, ADC

WLAN_PASSWORD =

led = Pin(2, Pin.OUT)
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
    wlan.connect('DTUdevice', WLAN_PASSWORD)
    time.sleep(5)
    ifconfig = wlan.ifconfig()
    ip_addr = ifconfig[0]
    print('ip: {}'.format(ip_addr))
    return wlan

def read_adc(adc):
    avg_length = 2000
    sum = 0
    for i in range(0, avg_length):
        sum += adc.read_uv() / 1e6
    avg = sum / avg_length
    return avg

LOCATION = '263_turbo_pump_temperatures'
wlan = init_wlan()

timer = Timer(1)
led = Pin(2, Pin.OUT)
timer.init(period=100, mode=Timer.PERIODIC, callback=blink)

udpsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udpsocket.connect(('', 8500))

adc1 = ADC(Pin(36), atten=ADC.ATTN_0DB)
adc2 = ADC(Pin(39), atten=ADC.ATTN_0DB)
adc3 = ADC(Pin(34), atten=ADC.ATTN_0DB)
while True:
    time.sleep(5)

    connected = wlan.isconnected()
    print('Connected', connected)
    if not connected:
        timer.init(period=100, mode=machine.Timer.PERIODIC, callback=blink)
        print('Not connected to wifi -  try again')
        wlan.disconnect()
        time.sleep(2)
        wlan.connect('DTUdevice', WLAN_PASSWORD)
        time.sleep(5)
        continue
    timer.deinit()
    timer.init(period=2000, mode=machine.Timer.PERIODIC, callback=blink)

    t1 = read_adc(adc1) * 100
    t2 = read_adc(adc2) * 100
    t3 = read_adc(adc3) * 100

    msg = 'Deposition: {:.2f}C.  Old etching: {:.2f}C, New etching: {:.2f}C'
    print(msg.format(t3, t2, t1))

    data = {
      'location': LOCATION,
      'deposition_temperature': t3,
      'old_etching_temperature': t2,
      'new_etching_temperature': t1,
    }
    udp_string = 'json_wn#' + json.dumps(data)
    print(udp_string)
    try:
        udpsocket.sendto(udp_string, ('10.196.161.242', 8500))
        led_show_ok()
    except OSError:
        print('Did not manage to send udp')
    print()
