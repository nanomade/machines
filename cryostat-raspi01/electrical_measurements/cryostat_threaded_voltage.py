import time
import pyvisa


class BackgroundMeasure():
    def __init__(self):
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
        self.voltage = voltage


class MeasureVTotal(BackgroundMeasure):
    def __init__(self, dmm):
        super().__init__()
        self.dmm = dmm

    def start_measurement(self):
        voltage = self.dmm.next_reading()
        self.voltage = voltage
