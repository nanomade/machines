import time
import serial
import threading

PORT = '/dev/serial/by-id/'
PORT = PORT + 'usb-STMicroelectronics_STM32_Virtual_ComPort_4994387C3550-if00'


class DeflectorReader(threading.Thread):
    def __init__(self):
        super().__init__()
        self.ser = serial.Serial(PORT, 38400, timeout=0.2)
        self.latest_read = 0
        self.running = True
        self.data = {}
        self.data_available = False

    def _parse_limited(self, reply):
        p = int(reply)
        # Time is not returned, time_ok is always true
        data = {'p': p, 'time_ok': True}
        return data

    def _parse_full(self, reply):
        fields = reply.split(b',')
        dt_expected = int(fields[0])
        dt_actual = (time.time() - self.latest_read) * 1000
        # print(dt_expected, dt_actual)
        p = int(fields[1])  # Pa
        t = int(fields[2]) / 100  # C
        p_ref = int(fields[3])  # Pa
        t_ref = int(fields[4]) / 100  # C
        time_ok = abs(dt_expected - dt_actual) < 5
        data = {'p': p, 't': t, 'p_ref': p_ref, 't_ref': t_ref, 'time_ok': time_ok}
        return data

    def stop(self):
        self.running = False

    def read_from_sensor(self):
        reply = self.ser.readline().strip()
        if len(reply) == 0:
            self.data_available = False
            return {}

        if b',' in reply:
            data = self._parse_full(reply)
        else:
            data = self._parse_limited(reply)
        self.latest_read = time.time()
        return data

    def return_data(self, only_new_data=True):
        if only_new_data and not self.data_available:
            return None
        self.data_available = False
        return self.data

    def run(self):
        while self.running:
            data = self.read_from_sensor()
            if data['time_ok']:
                self.data = data
                self.data_available = True


def main():
    dr = DeflectorReader()
    dr.start()
    while dr.running:
        time.sleep(0.01)
        print(dr.return_data())
        # time.sleep(1)


if __name__ == '__main__':
    main()
