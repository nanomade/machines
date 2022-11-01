import time
import json
import socket
import network

# import machine
from machine import Timer, Pin

def amphenol_read(i2c):
    time.sleep(0.1)
    result = i2c.readfrom_mem(0x28, 0, 4)

    temp = result[2]
    temp = temp << 8
    temp = temp | result[3]
    temp = temp >> 5

    # Forumla borrowed from data-sheet for DLVR
    temperature = temp * (200.0/2047) - 50
    # Interestingly, this also works....
    # temperature = ((temp / 10.0) - 32) * 5.0 / 9.0  # 10xF to C                                 

    pres = result[0] & 0x3f  # Leftmost two bits are status bits, ignore                        
    pres = pres << 8
    pres = pres | result[1]
    pressure = pres * 68.9476 / 1000  # PSI to mbar
    return temperature, pressure

def blink(t):
    led.value(not led.value())

def led_show_ok():
    print('led on')
    led.value(0)
    time.sleep(0.5)
    print('led off')
    led.value(1)
    
LOCATION = '309_000'
timer = Timer(1)

sda = Pin(4)
scl = Pin(5)
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
    
    temperature, pressure = amphenol_read(i2c)
    # msg = 'Temperature: {:.1f}C. Pressure: {:.2f}mbar'
    # print(msg.format(temperature, pressure))
    data = {
      'location': LOCATION,
      'temperature': temperature,
      'house_vacuum_pressure': pressure
    }
    udp_string = 'json_wn#' + json.dumps(data)
    print(udp_string, ip_addr)
    try:
        udpsocket.sendto(udp_string, ('10.199.253.148', 8500))
        led_show_ok()
    except OSError:
        print('Did not manage to send udp')
    print()

