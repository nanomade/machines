import time
import json
import threading

from PyExpLabSys.common.sockets import DataPushSocket
from PyExpLabSys.common.sockets import DateDataPullSocket

# from cryostat_measurement import CrystatMeasurement
# Moving away from CryostatMeasurement and into importing modules directly

from cryostat_4point_dc import Cryostat4PointDC
from cryostat_delta_constant_current import CryostatDeltaConstantCurrent
from cryostat_diff_conductance import CryostatDifferentialConductance
from cryostat_constant_current_gate_sweep import CryostatConstantCurrentGateSweep

class CryostatController(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.quit = False
        # self.cm = CrystatMeasurement()
        self.measurement = None

        self.pushsocket = DataPushSocket('cryostat', action='enqueue', port=8510)
        self.pushsocket.start()

        self.pullsocket = DateDataPullSocket(
            'cryostat', ['status', 'v_xx'], timeouts=[999999, 3], port=9002
        )
        self.pullsocket.start()

    def start_ac_4_point(self, i_from, i_to, i_steps, **kwargs):
        """
        **kwargs is not actually used, but will eat keywords
        originating from the network syntax.
        """
        # TODO: Check that measurement is not already running
        # TODO: steps
        t = threading.Thread(target=self.cm.ac_4_point_measurement,
                             args=(i_from, i_to, i_steps))
        t.start()
        return True

    def start_dc_4_point(self, **kwargs):
        # TODO: Check that measurement is not already running
        del(self.measurement)
        self.measurement = Cryostat4PointDC()
        t = threading.Thread(
            target=self.measurement.dc_4_point_measurement,
            kwargs=kwargs
        )
        t.start()
        return True

    def start_diff_conductance(self, **kwargs):
        # TODO: Check that measurement is not already running
        del(self.measurement)
        self.measurement = CryostatDifferentialConductance()
        t = threading.Thread(
            target=self.measurement.differential_conductance_measurement,
            kwargs=kwargs
        )
        t.start()
        return True

    def start_delta_constant_current(self, **kwargs):
        # TODO: Check that measurement is not already running
        del(self.measurement)
        self.measurement = CryostatDeltaConstantCurrent()
        t = threading.Thread(
            target=self.measurement.delta_constant_current,
            kwargs=kwargs
        )
        t.start()
        return True

    def start_constant_current_gate_sweep(self, **kwargs):
        # TODO: Check that measurement is not already running
        del(self.measurement)
        self.measurement = CryostatConstantCurrentGateSweep()
        t = threading.Thread(
            target=self.measurement.constant_current_gate_sweep,
            kwargs=kwargs
        )
        t.start()
        return True

    def _handle_element(self, element):
        cmd = element.get('cmd')
        if cmd == 'start_measurement':
            # if element.get('measurement') == 'ac_4_point':
            #     self.start_ac_4_point(**element)
            if element.get('measurement') == 'dc_4_point':
                self.start_dc_4_point(**element)
            if element.get('measurement') == 'diff_conductance':
                self.start_diff_conductance(**element)
            if element.get('measurement') == 'delta_constant_current':
                self.start_delta_constant_current(**element)
            if element.get('measurement') == 'constant_current_gate_sweep':
                self.start_constant_current_gate_sweep(**element)

        elif cmd == 'abort':
            if self.measurement is not None:
                self.measurement.abort_measurement()

        elif cmd == 'lock_in_frequency':
            freq = element.get('frequency')
            print('Set lock in frequency to {}Hz'.format(freq))
            self.cm.set_lock_in_frequency(freq)

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

            status = {'type': None, 'start_time': None}
                
            if self.measurement is not None:
                if len(self.measurement.current_measurement['v_xx']) > 2:
                    self.pullsocket.set_point_now(
                        'v_xx',
                        self.measurement.current_measurement['v_xx'][-1]
                    )

                status = {
                    'type': self.measurement.current_measurement['type'],
                    'start_time': self.measurement.current_measurement['start_time'],
                }

                    
            self.pullsocket.set_point_now('status', status)


def main():
    cc = CryostatController()
    # cm.dc_4_point_measurement(1e-6, 1e-4)
    cc.start()


if __name__ == '__main__':
    main()
