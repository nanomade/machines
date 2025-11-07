import time
from PyExpLabSys.drivers.keithley_2182 import Keithley2182
from PyExpLabSys.drivers.keithley_2400 import Keithley2400
from PyExpLabSys.drivers.keithley_6220 import Keithley6220

current_source = Keithley6220(interface='lan', hostname='192.168.0.3')
smu = Keithley2400(interface='gpib', gpib_address=22)

xy_nanov = Keithley2182(
    interface='serial',
    device='/dev/serial/by-id/usb-Prolific_Technology_Inc._USB-Serial_Controller_D-if00-port0',
)


smu.set_source_function('v')
# Line 2 is also used by 6221 delta mode
smu.scpi_comm(':TRIGGER:OLINE 2')
# Force a trigger by performing a measurement
smu.scpi_comm(':TRIGGER:OUTPUT SENSE')
smu.set_voltage(0.1)
smu.output_state(True)

print(smu.scpi_comm(':TRIGGER:OUTPUT SENSE'))

for i in range(0, 10):
    print()
    voltage = smu.read_voltage()
    current = smu.read_current()
    print('Current: {:.1f}uA. Voltage: {:.2f}mV. Resistance: {:.1f}ohm'.format(
        current * 1e6, voltage * 1000, voltage / current))
    current_source._2182a_comm(':DATA:FRESH?')
    print('nv1: ', current_source._2182a_comm())
    print('nv2: ', xy_nanov.scpi_comm(':DATA:FRESH?'))
    print('---')

exit()

# print(smu.scpi_comm(':TRIGGER:OUTPUT?'))
smu.output_state(True)


for i in range(0, 10):
    smu.set_voltage(i/10.0)
    time.sleep(0.5)
    print(smu.scpi_comm(':TRIGGER:OUTPUT SENSE'))
    current = smu.read_current()
    print(smu.scpi_comm(':TRIGGER:OUTPUT NONE'))
    voltage = smu.read_voltage()
    print('Current: {:.1f}uA. Voltage: {:.2f}mV. Resistance: {:.1f}ohm'.format(
        current * 1e6, voltage * 1000, voltage / current))


# print(SMU.scpi_comm(':TRIGGER:OUTPUT:DELAY?'))

# current_source._2182a_comm(':READ?')
