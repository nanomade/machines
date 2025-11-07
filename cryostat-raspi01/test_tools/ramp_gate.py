import time
from PyExpLabSys.drivers.keithley_2450 import Keithley2450

back_gate = Keithley2450(interface='lan', device='192.168.0.30')

back_gate.set_voltage(0)
exit()
for v in range(997, 0, -1):
    volt = v * 0.01
    back_gate.set_voltage(volt)
    time.sleep(0.1)
