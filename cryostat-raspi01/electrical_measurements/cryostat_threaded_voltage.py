import time


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
    def __init__(self, current_source):
        super().__init__()
        self.current_source = current_source

    def _start_measurement(self):
        self.current_source._2182a_comm(':STATus:QUEue:NEXT?')
        v_xx_error_queue = self.current_source._2182a_comm()
        # TODO! Read this into an network-accesible variable to show in frontend
        # print('Vxx error queue: ', v_xx_error_queue)
        self.current_source._2182a_comm(':DATA:FRESh?')
        value_raw = self.current_source._2182a_comm()

        # This seems to never trigger - consider to remove
        if len(value_raw) < 2:
            print('Try reading again')
            time.sleep(0.075)
            value_raw = self.current_source._2182a_comm()
            print('Second attempt: ', value_raw)

        try:
            value_raw = value_raw.replace(chr(0x13), '')
            # print('Vxx value raw: {}'.format(value_raw))
            voltage = float(value_raw)
        except ValueError:
            voltage = -1001
        self.voltage = voltage


class MeasureVxy(BackgroundMeasure):
    def __init__(self, nano_v):
        super().__init__()
        self.nano_v = nano_v

    def _start_measurement(self):
        try:
            voltage = self.nano_v.read_fresh()
        except TypeError:
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
