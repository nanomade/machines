import time
import json
import threading

from PyExpLabSys.common.sockets import DataPushSocket
from PyExpLabSys.common.sockets import DateDataPullSocket

from cryostat_measurement import CrystatMeasurement


class CryostatController(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.quit = False
        self.cm = CrystatMeasurement()

        self.pushsocket = DataPushSocket('cryostat', action='enqueue')
        self.pushsocket.start()

        self.pullsocket = DateDataPullSocket(
            'cryostat', ['status', 'data'], timeouts=[999999, 3], port=9000
        )

    def start_dc_4_point(self, i_from, i_to, i_steps, **kwargs):
        """
        **kwargs is not actually used, but will eat keywords
        originating from the network syntax.
        """
        # TODO: Check that measurement is not already running
        # TODO: steps
        t = threading.Thread(target=self.cm.dc_4_point_measurement,
                             args=(i_from, i_to, i_steps))
        t.start()
        return True

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

    def _handle_element(self, element):
        cmd = element.get('cmd')
        if cmd == 'start_measurement':
            if element.get('measurement') == 'ac_4_point':
                self.start_ac_4_point(**element)
            if element.get('measurement') == 'dc_4_point':
                self.start_dc_4_point(**element)

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
            qsize = self.pushsocket.queue.qsize()
            while qsize > 0:
                element = self.pushsocket.queue.get()
                qsize = self.pushsocket.queue.qsize()
                self._handle_element(element)

            current_data = json.dumps(self.cm.current_measurement)
            self.pullsocket.set_point_now('data', current_data)


def main():
    cc = CryostatController()
    # cm.dc_4_point_measurement(1e-6, 1e-4)
    cc.start()


if __name__ == '__main__':
    main()
