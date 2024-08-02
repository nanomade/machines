import time
import pyvisa


class BackgroundMeasure():
    def __init__(self):
        self.t_start = None
        self.voltage = None

    def read_voltage(self):
        while self.voltage is None:
            time.sleep(0.01)
        voltage = self.voltage
        self.voltage = None
        return voltage

    def _start_measurement(self):
        raise NotImplementedError

    def start_measurement(self, nplc=1):
        self.t_start = time.time()
        # Sleep a bit less than the integration time
        time.sleep(nplc * 0.02 * 0.9)
        self._start_measurement()


class MeasureVxx(BackgroundMeasure):
    def __init__(self, nano_v):
        super().__init__()
        self.nano_v = nano_v

    def _start_measurement(self):
        try:
            voltage = self.nano_v.read_fresh()
        except pyvisa.errors.VisaIOError:
            voltage = None
        if voltage is None:
            voltage = -1001
        msg = 'Vxx: Voltage: {:.3f}. Time: {:.0f}ms'
        # print(msg.format(voltage, 1000 * (time.time() - self.t_start)))
        self.voltage = voltage

class MeasureVxy(BackgroundMeasure):
    def __init__(self, nano_v):
        super().__init__()
        self.nano_v = nano_v

    def _start_measurement(self):
        try:
            voltage = self.nano_v.read_fresh()
        except pyvisa.errors.VisaIOError:
            voltage = None
        if voltage is None:
            voltage = -1001
        msg = 'Vxy: Voltage: {:.3f}. Time: {:.0f}ms'
        # print(msg.format(voltage, 1000 * (time.time() - self.t_start)))
        self.voltage = voltage


class MeasureVTotal(BackgroundMeasure):
    def __init__(self, dmm):
        super().__init__()
        self.dmm = dmm

    def _start_measurement(self):
        voltage = self.dmm.next_reading()
        msg = 'DMM: Voltage: {:.3f}. Time: {:.0f}ms'
        # print(msg.format(voltage, 1000 * (time.time() - self.t_start)))
        self.voltage = voltage
