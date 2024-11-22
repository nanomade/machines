import json
import time
import socket
import network
import machine
import ubinascii

WLAN_PASSWORD =

CALIBRATION = {  # Frequency to GPM, with low-flow adapter installed
    0: 0,
    13: 0.1,
    41: 0.25,
    90: 0.5,
    137: 0.75,
    186: 1.0,
    280: 2.0,  # This point is not official, but including to avoid overrun
}

def init_wlan():
    print('Connect to network')
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    mac = ubinascii.hexlify(network.WLAN().config('mac'),':').decode()
    print(mac)
    wlan.connect('DTUdevice', WLAN_PASSWORD)
    time.sleep(5)
    ifconfig = wlan.ifconfig()
    ip_addr = ifconfig[0]
    print('ip: {}'.format(ip_addr))
    return wlan


def frequency_to_flow(freq):
    # Code stolen from pirani logger for glove boxes
    if freq <= 0:
        return 0

    prev_ref = 0
    for ref in sorted(CALIBRATION.keys()):
        if ref > freq:
            break
        prev_ref = ref

    fraction = (freq - prev_ref) / (ref - prev_ref)
    diff = CALIBRATION[ref] - CALIBRATION[prev_ref]
    flow = CALIBRATION[prev_ref] + diff * fraction
    lpm = flow * 3.78541
    return lpm

def blink(timer):
    LED.toggle()


def _read_single_count(pin):
    value = pin.value()
    t = time.ticks_us()
    dt = 0
    while pin.value() == value:
        dt = time.ticks_us() - t
        if dt > 1e6:
            print('No water flow')
            break
    return dt


def read_flow(pin, pulse_count=600):
    # First read is not valid, but has to return a value
    dt = _read_single_count(pin)
    if dt > 1e6:
        return 0

    # Read 10 pulses:
    t_total = 0
    no_flow = False
    for i in range(0, pulse_count):
        dt = _read_single_count(pin)
        if dt > 1e6:
            no_flow = True
            break
        t_total += dt
    
    if no_flow:
        return 0
    
    avg_dt = 1.0 * t_total / pulse_count

    avg_freq = 1e6/avg_dt
    flow = frequency_to_flow(avg_freq)
    print('Flow is: {:.4f}L/min'.format(flow))
    return flow


LOCATION = '309_263'
LED = machine.Pin("LED", machine.Pin.OUT)
TEMP_ADC = machine.ADC(4)

# Excitaton voltage for old Moorfield plasma echer
p0 = machine.Pin(0, machine.Pin.OUT)
p0.high()
# Read for old Moorfield plasma etcher
p22 = machine.Pin(22, machine.Pin.IN, machine.Pin.PULL_UP)

# for i in range(0, 100):
#     print(p22.value())
# 1/0

udpsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udpsocket.connect(('', 8500))

timer = machine.Timer()
timer.init(freq=10, mode=machine.Timer.PERIODIC, callback=blink)
wlan = init_wlan()
while True:
    time.sleep(2)

    connected = wlan.isconnected()
    if not connected:
        timer.init(freq=10.0, mode=machine.Timer.PERIODIC, callback=blink)
        print('Not connected to wifi -  try again')
        wlan.disconnect()
        time.sleep(2)
        wlan.connect('DTUdevice', WLAN_PASSWORD)
        time.sleep(5)
        continue

    timer.init(freq=1.0, mode=machine.Timer.PERIODIC, callback=blink)

    temp_v = TEMP_ADC.read_u16() * (3.3 / (65535))
    temperature = 27 - (temp_v - 0.706)/0.001721

    old_etcher_cwf = read_flow(p22)

    data = {
      'location': LOCATION,
      'old_etcher_cooling_water_flow': old_etcher_cwf,
      'moorfield_colling_water_pico_temperature': temperature,
    }
    udp_string = 'json_wn#' + json.dumps(data)
    print(udp_string)
    try:
        udpsocket.sendto(udp_string, ('10.196.161.242', 8500))
    except OSError:
        print('Did not manage to send udp')
