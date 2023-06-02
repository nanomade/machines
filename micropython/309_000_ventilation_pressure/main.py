import json
import time
import socket
import network
import machine
from machine import Pin

LOCATION = '309_000'
PRESSURE_SCALE = 60.0

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


def convert_twos_comp(val):
    if val > (2**15 - 1):
        val = val - 2**16
    return val

def read_pressure(avg_length=10):
    pressure_sum = 0
    for i in range(0, avg_length):
        time.sleep(0.05)
        val = I2C.readfrom_mem(0x40, 0xF1, 3)
        msb = val[0]
        lsb = val[1]
        crc = val[2]
        # Todo: Calculate crc?
        pressure = convert_twos_comp(msb*256 + lsb) / PRESSURE_SCALE
        pressure_sum += pressure
        # print(pressure)
    avg_pressure = pressure_sum / avg_length
    return avg_pressure

def blink(timer):
    LED.toggle()

p2 = Pin(2, Pin.IN, Pin.PULL_UP)
p3 = Pin(3, Pin.IN, Pin.PULL_UP)
LED = machine.Pin("LED", machine.Pin.OUT)
I2C = machine.SoftI2C(scl=machine.Pin(3), sda=machine.Pin(2), freq=100_000)
TEMP_ADC = machine.ADC(4)

udpsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udpsocket.connect(('', 8500))

timer = machine.Timer()
timer.init(freq=10, mode=machine.Timer.PERIODIC, callback=blink)
wlan = init_wlan()

while True:
    time.sleep(1)
    # ifconfig = wlan.ifconfig()
    # ip_addr = ifconfig[0]
    connected = wlan.isconnected()
    if not connected:
        timer.init(freq=10.0, mode=machine.Timer.PERIODIC, callback=blink)
        print('Not connected to wifi -  try again')
        wlan.disconnect()
        time.sleep(2)
        wlan.connect('device')
        time.sleep(5)
        continue

    timer.init(freq=1.0, mode=machine.Timer.PERIODIC, callback=blink)
    
    pressure = read_pressure(30)
    temp_v = TEMP_ADC.read_u16() * (3.3 / (65535))
    temperature = 27 - (temp_v - 0.706)/0.001721

    data = {
      'location': LOCATION,
      'ventilation_pressure': pressure,
      'ventilation_picotemperature': temperature,
    }
    udp_string = 'json_wn#' + json.dumps(data)
    print(udp_string)
    try:
        udpsocket.sendto(udp_string, ('10.199.253.148', 8500))
    except OSError:
        print('Did not manage to send udp')

    