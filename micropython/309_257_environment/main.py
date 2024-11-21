import json
import time
import socket
import network
import machine
import ubinascii

from qmp6988 import QMP6988 
from sht30 import SHT30

WLAN_PASSWORD = 

def init_wlan():
    print('Connect to network')
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    mac = ubinascii.hexlify(network.WLAN().config('mac'),':').decode()
    print('mac: ', mac)
    wlan.connect('DTUdevice', WLAN_PASSWORD)
    time.sleep(5)
    ifconfig = wlan.ifconfig()
    ip_addr = ifconfig[0]
    print('ip: {}'.format(ip_addr))
    return wlan


def blink(timer):
    LED.toggle()


LOCATION = '309_257'
TEMP_ADC = machine.ADC(4)
LED = machine.Pin("LED", machine.Pin.OUT)

i2c = machine.SoftI2C(scl=machine.Pin(27), sda=machine.Pin(26), freq=100000)
devices = i2c.scan()
print(devices)

barometer = QMP6988(i2c)
for _ in range(0, 5):
    # Ensure qmp6988 is ready
    barometer.measure()
    
thermometer = SHT30(i2c)
for _ in range(0, 5):
    # Ensure sht30 is ready
    thermometer.measure()

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
        wlan.connect('DTUdevice', WLAN_PASSWORD)
        time.sleep(5)
        continue

    timer.init(freq=2.0, mode=machine.Timer.PERIODIC, callback=blink)

    temp_v = TEMP_ADC.read_u16() * (3.3 / (65535))
    pico_temperature = 27 - (temp_v - 0.706)/0.001721

    temperature, humidity = thermometer.measure()
    _, air_pressure = barometer.measure()

    data = {
      'location': LOCATION,
      'pico_temperature': pico_temperature,
      'temperature': temperature,
      'humidity': humidity,
      'air_pressure': air_pressure / 100.0,
    }
    udp_string = 'json_wn#' + json.dumps(data)
    print(udp_string)
    try:
        udpsocket.sendto(udp_string, ('10.196.161.242', 8500))
    except OSError:
        print('Did not manage to send udp')
