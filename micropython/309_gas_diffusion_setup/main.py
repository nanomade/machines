import time
import json
import network
import socket
import machine
from ads1x15 import ADS1115

led = machine.Pin("LED", machine.Pin.OUT)
def blink(t):
    led.value(not led.value())

def led_show_ok():
    led.value(1)
    time.sleep(0.5)
    led.value(0)

def init_timer():   
    timer = machine.Timer()
    timer.init(period=5000, mode=machine.Timer.PERIODIC, callback=blink)
    return timer


def init_i2c():
    sda = machine.Pin(2)
    scl = machine.Pin(3)
    i2c = machine.SoftI2C(sda=sda, scl=scl, freq=10000)
    print(i2c.scan())
    return i2c


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


LOCATION = '309_gas_diffusion_setup'
timer = init_timer()
i2c = init_i2c()
wlan = init_wlan()

udpsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udpsocket.connect(('', 8500))


ads = ADS1115(i2c, address=0x48, gain=0)
while True:
    time.sleep(5)
    # ifconfig = wlan.ifconfig()
    # ip_addr = ifconfig[0]
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

    v1_raw = ads.read(rate=0, channel1=0, channel2=1)
    scaled_v1 = ads.raw_to_v(v1_raw)
    v1 = scaled_v1 * 2.53  # Calibrate in-situ

    v2_raw = ads.read(rate=0, channel1=2, channel2=3)
    scaled_v2 = ads.raw_to_v(v2_raw)
    v2 = scaled_v2 * 2.53  # Calibrate in-situ

    exp1 = 0.778 * (v1 - 6.143)  # mbar, use 6.304 for torr
    exp2 = 0.778 * (v2 - 6.143)
    p_gas_side = 10.0**exp1
    p_pump_side = 10.0**exp2

    msg = 'V1 ({} counts): {:.2f}V.  V2 ({} counts): {:.2f}V'
    print(msg.format(v1_raw, v1, v2_raw, v2))


    data = {
      'location': LOCATION,
      'p_gas_side': p_gas_side,
      'p_pump_side': p_pump_side
    }
    udp_string = 'json_wn#' + json.dumps(data)
    print(udp_string)
    try:
        udpsocket.sendto(udp_string, ('10.199.253.148', 8500))
        led_show_ok()
    except OSError:
        print('Did not manage to send udp')
    print()
