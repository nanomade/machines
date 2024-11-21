import json
import time
import socket
import network
import machine
import ubinascii


# Pinout of Edwards RJ45 wire;
# 7: hvid
# 5: blå
# 3: lysserød
# 2: brun
# 1: rød

WLAN_PASSWORD = 

# <2.05 under range
EDWARDS_CALIBRATION = {
    0: 0,  # Really, this means values lower than 2.05 in not measurable
    # In our case we will never get this low.
    2.05: 8.26e-5,
    2.1: 2.27e-4,
    2.2: 5.00e-4,
    2.4: 1.08e-3,
    2.6: 1.68e-3,
    2.8: 2.60e-3,
    3.0: 3.84e-3,
    3.2: 5.15e-3,
    3.4: 6.87e-3,
    3.6: 1.05e-2,
    3.7: 1.56e-2,
    4.0: 2.10e-2,
    4.2: 2.77e-2,
    4.4: 3.45e-2,
    4.6: 4.16e-2,
    4.8: 5.04e-2,
    5.0: 5.92e-2,
    5.2: 8.74e-2,
    5.4: 1.27e-1,
    5.6: 1.71e-1,
    5.8: 2.23e-1,
    6.0: 2.90e-1,
    6.2: 3.57e-1,
    6.4: 4.35e-1,
    6.6: 5.33e-1,
    6.8: 6.40e-1,
    7.0: 7.67e-1,
    7.2: 9.23e-1,
    7.4: 1.14,
    7.6: 1.40,
    7.8: 1.66,
    8.0: 1.92,
    8.2: 2.38,
    8.4: 2.95,
    8.6: 3.51,
    8.8: 4.17,
    9.0: 5.40,
    9.2: 7.06,
    9.4: 9.69,
    9.5: 12.9,
    9.6: 16.6,
    9.7: 20.7,
    9.8: 33.9,
    9.9: 63.2,
    9.95: 144.0,
    10.0: 1000.0,
    11.0: 1000.0,
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

def voltage_to_pressure(voltage):
    if voltage < 0:
        return 0

    prev_ref_v = 0
    for ref_v in sorted(EDWARDS_CALIBRATION.keys()):
        if ref_v > voltage:
            break
        prev_ref_v = ref_v

    fraction = (voltage - prev_ref_v) / (ref_v - prev_ref_v)
    # print(prev_ref_v, ref_v)
    p_diff = EDWARDS_CALIBRATION[ref_v] - EDWARDS_CALIBRATION[prev_ref_v]
    p = EDWARDS_CALIBRATION[prev_ref_v] + p_diff * fraction
    
    if p < 1e-4:
        p = 1e-4
    
    return p

def analog_read():
    v = ADC.read_u16()
    if v > 2**15:
        avg_length = 500
    else:
        avg_length = 50
    # todo: add measurement of v_ref and v_grnd to correct for measurement
    # errors. For now simply return the value
    
    v_raw = 0
    for i in range(0, avg_length):
        v_raw += ADC.read_u16()
        time.sleep(0.001)
    v_raw = 1.0 * v_raw / avg_length
    # Here we should subtract the ground reading, but so far just subtract a typical value
    v_raw = v_raw - 320
    
    v_scaled = 3.3 * v_raw / (2**16 - 1)
    
    # Measured manually
    adc_gain = 3.219383 / 3.1972
    v = v_scaled / adc_gain
    return v

def blink(timer):
    LED.toggle()

LOCATION = '309_moorfield_common_vacuum'
ADC = machine.ADC(26)
TEMP_ADC = machine.ADC(4)

LED = machine.Pin("LED", machine.Pin.OUT)
GAIN = 10.006 / 3.1978 # Gain of voltage divider

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
    print(wlan)
    print(wlan.isconnected())
    if not connected:
        timer.init(freq=10.0, mode=machine.Timer.PERIODIC, callback=blink)
        print('Not connected to wifi -  try again')
        wlan.disconnect()
        time.sleep(2)
        wlan.connect('DTUdevice', WLAN_PASSWORD)
        time.sleep(5)
        continue

    timer.init(freq=1.0, mode=machine.Timer.PERIODIC, callback=blink)
    v = analog_read() * GAIN
    pressure = voltage_to_pressure(v)

    temp_v = TEMP_ADC.read_u16() * (3.3 / (65535))
    temperature = 27 - (temp_v - 0.706)/0.001721
    
    msg = 'V: {:.23}V. P {:.5f}mbar. T: {:.2f}'
    # print(v, pressure)
    
    data = {
      'location': LOCATION,
      'pressure': pressure,
      'temperature': temperature,
    }
    udp_string = 'json_wn#' + json.dumps(data)
    print(udp_string)
    try:
        udpsocket.sendto(udp_string, ('10.196.161.242', 8500))
    except OSError:
        print('Did not manage to send udp')
