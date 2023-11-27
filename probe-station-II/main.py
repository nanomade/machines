import time
import threading

from PyExpLabSys.common.sockets import DataPushSocket
from PyExpLabSys.common.sockets import DateDataPullSocket

from ps_measurement_base import ProbeStationMeasurementBase

from ps_double_stepped_4point_dc import ProbeStation4PointDoubleStepped


class ProbeStationController(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.quit = False

        self.measurement = ProbeStationMeasurementBase()

        self.pushsocket = DataPushSocket('probe_station', action='enqueue', port=8510)
        self.pushsocket.start()

        self.pullsocket = DateDataPullSocket(
            'probestation',
            ['status', 'v_xx', 'v_tot'],
            timeouts=[999999, 3, 3],
            port=9002,
        )
        self.pullsocket.start()

    def start_4point_double_stepped(self, **kwargs):
        # TODO: Check that measurement is not already running
        del self.measurement
        self.measurement = ProbeStation4PointDoubleStepped()
        t = threading.Thread(
            target=self.measurement.dc_4_point_measurement, kwargs=kwargs
        )
        t.start()
        return True

    def _handle_element(self, element):
        cmd = element.get('cmd')
        if cmd == 'start_measurement':
            # This only works on first run - change into check for
            if self.measurement.current_measurement['type'] is not None:
                print('Measurement running, cannot start new')
                return
            if element.get('measurement') == '4point_double_stepped':
                self.start_4point_double_stepped(**element)

        elif cmd == 'abort':
            if self.measurement.current_measurement['type'] is None:
                self.measurement.abort_measurement()

        elif cmd == 'set_manual_gate':
            if self.measurement.current_measurement['type'] is None:
                voltage = element.get('gate_voltage', 0)
                current_limit = element.get('gate_current_limit', 1e-8)
                self.measurement.back_gate.set_source_function('v')
                self.measurement.back_gate.set_current_limit(current_limit)
                self.measurement.back_gate.set_voltage(voltage)
                self.measurement.back_gate.output_state(True)

        # elif cmd == 'toggle_6221':
        #     if self.measurement.current_measurement['type'] is None:
        #         state = self.measurement.current_source.output_state()
        #         self.measurement.current_source.output_state(not state)

        # elif cmd == 'lock_in_frequency':
        #     freq = element.get('frequency')
        #     print('Set lock in frequency to {}Hz'.format(freq))
        #     self.cm.set_lock_in_frequency(freq)

        else:
            print('Unknown command')

    def run(self):
        while not self.quit:
            time.sleep(1)
            print('Running')
            # Check if measurement is running and set self.measurement to None of not
            qsize = self.pushsocket.queue.qsize()
            while qsize > 0:
                element = self.pushsocket.queue.get()
                qsize = self.pushsocket.queue.qsize()
                self._handle_element(element)

            # Do not feed socket with old data, update v_xx only if a measurement
            # is running
            if self.measurement.current_measurement['type'] is not None:
                if len(self.measurement.current_measurement['v_xx']) > 2:
                    self.pullsocket.set_point_now(
                        'v_xx', self.measurement.current_measurement['v_xx'][-1]
                    )
            status = {
                'type': self.measurement.current_measurement['type'],
                'start_time': self.measurement.current_measurement['start_time'],
            }
            self.pullsocket.set_point_now('status', status)

            if self.measurement.current_measurement['type'] is None:
                # gate_v = self.measurement.read_gate(store_data=False)
                # print(gate_v)
                self.measurement.dmm.set_trigger_source(external=False)
                self.measurement.dmm.set_range(0)
                # voltage = self.measurement.dmm.next_reading()
                voltage = self.measurement.dmm.read_dc_voltage()
                self.pullsocket.set_point_now('v_tot', voltage)


def main():
    pc = ProbeStationController()
    # cm.dc_4_point_measurement(1e-6, 1e-4)
    pc.start()


if __name__ == '__main__':
    main()
