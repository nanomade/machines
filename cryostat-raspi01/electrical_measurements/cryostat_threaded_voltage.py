import time


class BackgroundMeasure():
    def __init__(self, nplc):
        self.voltage = None
        self.nplc = nplc

    def read_voltage(self):
        while self.voltage is None:
            time.sleep(0.01)
        voltage = self.voltage
        self.voltage = None
        return voltage

    def start_measurement(self):
        raise NotImplementedError


class MeasureVxx(BackgroundMeasure):
    def __init__(self, current_source, nplc):
        super().__init__(nplc)
        self.current_source = current_source

    def start_measurement(self):
        # Sleep a bit less than the integration time
        time.sleep(self.nplc * 0.02 * 0.9)
        self.current_source._2182a_comm(':DATA:FRESh?')
        value_raw = self.current_source._2182a_comm()
        try:
            value_raw = value_raw.replace(chr(0x13), '')
            voltage = float(value_raw)
        except ValueError:
            voltage = -1001
        self.voltage = voltage


class MeasureVxy(BackgroundMeasure):
    def __init__(self, nano_v, nplc):
        super().__init__(nplc)
        self.nano_v = nano_v

    def start_measurement(self):
        # Sleep a bit less than the integration time
        time.sleep(self.nplc * 0.02 * 0.9)
        voltage = self.nano_v.read_fresh()
        if voltage is None:
            voltage = -1001
        self.voltage = voltage


class MeasureVTotal(BackgroundMeasure):
    def __init__(self, dmm, nplc=None):
        super().__init__(nplc)
        self.dmm = dmm

    def start_measurement(self):
        voltage = self.dmm.next_reading()
        self.voltage = voltage
