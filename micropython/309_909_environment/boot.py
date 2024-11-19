import time
import json
import socket
import network

import machine

import sht30
import bme280

LOCATION = '309_909'

WLAN_PASSWORD =

# Connect to network
print('Connect to wifi')
sta_if = network.WLAN(network.STA_IF)
sta_if.active(True)

print('Connecting...')
sta_if.connect('DTUdevice', WLAN_PASSWORD)
time.sleep(5)
ifconfig = sta_if.ifconfig()
ip_addr = ifconfig[0]
print('ip: {}'.format(ip_addr))

time.sleep(2.5)

# For now, these are the pins we use
sda = machine.Pin(21)
scl = machine.Pin(22)

# i2c = machine.I2C(1, sda=sda, scl=scl, freq=10000)
i2c = machine.SoftI2C(sda=sda, scl=scl, freq=10000)
# scan_list = i2c.scan()

udpsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udpsocket.connect(('', 8500))

bme = bme280.BME280(i2c=i2c)
sht = sht30.SHT30(i2c=i2c)
while True:
    time.sleep(5)
    ifconfig = sta_if.ifconfig()
    ip_addr = ifconfig[0]
    connected = sta_if.isconnected()
    print('Connected', connected)
    if not connected:
        print('Not connected to wifi -  try again')
        sta_if.disconnect()
        time.sleep(2)
        sta_if.connect('DTUdevice', WLAN_PASSWORD)
        time.sleep(5)
        continue

    air_pressure_temp, air_pressure = bme.values
    temperature, humidity = sht.measure()

    data = {
      'location': LOCATION,
      'temperature': temperature,
      'temperature_airpressure': air_pressure_temp,
      'humidity': humidity,
      'air_pressure': air_pressure
    }
    udp_string = 'json_wn#' + json.dumps(data)
    print(udp_string, ip_addr)
    try:
        udpsocket.sendto(udp_string, ('10.196.161.242', 8500))
    except OSError:
        print('Did not manage to send udp')
    print()
