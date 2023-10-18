import time
import json
import socket
import network

import machine
import machine
from machine import Pin, Timer

import bme680

def blink(t):
    led.value(not led.value())

def led_show_ok():
    led.value(1)
    time.sleep(0.5)
    led.value(0)


LOCATION = '309_257_SPINNER_FUMEHOOD'
timer = Timer(1)

sda = machine.Pin(4)
scl = machine.Pin(5)
led = Pin(2, Pin.OUT)
timer.init(period=100, mode=Timer.PERIODIC, callback=blink)

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

i2c = machine.SoftI2C(sda=sda, scl=scl, freq=10000)

udpsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udpsocket.connect(('', 8500))

bme = bme680.BME680_I2C(i2c)
while True:
    time.sleep(5)
    ifconfig = sta_if.ifconfig()
    ip_addr = ifconfig[0]
    connected = sta_if.isconnected()
    print('Connected', connected)
    if not connected:
        timer.init(period=100, mode=Timer.PERIODIC, callback=blink)
        print('Not connected to wifi -  try again')
        sta_if.disconnect()
        time.sleep(2)
        sta_if.connect('device')
        time.sleep(5)
        continue
    timer.deinit()
    timer.init(period=2000, mode=Timer.PERIODIC, callback=blink)
    temperature = bme.temperature
    humidity = bme.humidity
    air_pressure = bme.pressure
    gas_resistance = bme.gas

    data = {
      'location': LOCATION,
      'temperature': temperature,
      'humidity': humidity,
      'gas_resistance': gas_resistance,
      'air_pressure': air_pressure
    }
    udp_string = 'json_wn#' + json.dumps(data)
    print(udp_string, ip_addr)
    try:
        udpsocket.sendto(udp_string, ('10.199.253.148', 8500))
        led_show_ok()
    except OSError:
        print('Did not manage to send udp')
    print()