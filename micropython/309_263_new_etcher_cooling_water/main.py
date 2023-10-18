import esp32
import time
import json
import socket
import network
import machine

CALIBRATION = {  # Frequency to GPM, with low-flow adapter installed
    0: 0,
    13: 0.1,
    41: 0.25,
    90: 0.5,
    137: 0.75,
    186: 1.0,
    280: 2.0,  # This point is not official, but including to avoid overrun
}

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
    time.sleep(8)
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

SINGLE_READ_NO_WATETR_FLOW = ''
def _read_single_count(pin):
    global SINGLE_READ_NO_WATETR_FLOW
    value = pin.value()
    t = time.ticks_us()
    dt = 0
    SINGLE_READ_NO_WATETR_FLOW = 'Flow'
    while pin.value() == value:
        dt = time.ticks_us() - t
        if dt > 1e6:
            print('No water flow')
            SINGLE_READ_NO_WATETR_FLOW = 'No flow'
            break
    return dt

def read_flow(pin, pulse_count=100):
    # First read is not valid, but has to return a value
    dt = _read_single_count(pin)
    if dt > 1e6:
        print('klaf')
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

#p0 = machine.Pin(0, machine.Pin.IN, machine.Pin.PULL_DOWN)
# p0 = machine.Pin(0, machine.Pin.IN)
p0 = machine.Pin(18, machine.Pin.IN)
adc = machine.ADC(machine.Pin(36))  # Blue

while True:
    time.sleep(1)
    connected = wlan.isconnected()
    # print('Connected', connected)
    if not connected:
        timer.init(period=100, mode=machine.Timer.PERIODIC, callback=blink)
        print('Not connected to wifi -  try again')
        wlan.disconnect()
        time.sleep(3)
        #wlan.connect('device')
        init_wlan()
        time.sleep(5)
        continue
    timer.deinit()
    timer.init(period=2000, mode=machine.Timer.PERIODIC, callback=blink)

    flow = read_flow(p0)

    t = read_temperature(adc, avg=1000)
    # msg = 'T: {:.2f}C. Flow {:.2f}L/min'
    # print(msg.format(t, flow))

    esp32_hall = esp32.hall_sensor()
    esp32_temp = 5.0 * (esp32.raw_temperature() - 32) / 9.0

    data = {
        'location': LOCATION,
        'new_etcher_cooling_water_flow': flow,
        'new_etcher_turbo_pump_temperature': t,
        'esp32_hall_sensor': esp32_hall,
        'esp32_temp': esp32_temp,
        'SINGLE_READ_NO_WATETR_FLOW': SINGLE_READ_NO_WATETR_FLOW,
    }
    udp_string = 'json_wn#' + json.dumps(data)
    print(udp_string)
    try:
        udpsocket.sendto(udp_string, ('10.199.253.148', 8500))
        led_show_ok()
    except OSError:
        print('Did not manage to send udp')
    print()

