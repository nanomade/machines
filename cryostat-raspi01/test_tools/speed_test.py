import time

t = time.time()
from PyExpLabSys.drivers.keithley_6220 import Keithley6220
dt = time.time() - t
print('Import time: {}'.format(dt))

current_source = Keithley6220(interface='lan', hostname='192.168.0.3')

t = time.time()
range_cmd = ':SENSE:VOLT:CHANNEL1:RANGE {:.2f}'.format(1)
plc_cmd ='SENSE:VOLTAGE:NPLCYCLES {}'.format(2)
current_source._2182a_comm(':CONF:VOLT')
current_source._2182a_comm(range_cmd)
current_source._2182a_comm(plc_cmd)
current_source._2182a_comm(':SAMP:COUNT 1')
dt = time.time() - t
print('2172a setup time: {}'.format(dt))



# self.current_source.set_voltage_limit(v_limit)
# self.current_source.set_current_range(stop)
# self.current_source.set_current(0)
# self.current_source.output_state(True)

