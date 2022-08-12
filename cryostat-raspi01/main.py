import time
import json
import logging
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

    def start_dc_4_point(self, i_from, i_to, steps, **kwargs):
        """
        **kwargs is not actually used, but will eat keywords
        originating from the network syntax.
        """
        # TODO: Check that measurement is not already running
        # TODO: steps
        t = threading.Thread(target=self.cm.dc_4_point_measurement,
                             args=(i_from, i_to, steps))
        t.start()
        return True

    def _handle_element(self, element):
        start = element.get('start_measurement')
        if start == 'dc_4_point_measurement':
            self.start_dc_4_point(**element)

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
            # todo: also update status
            
            #         value = (element[code], time.time())
            #         self.values[codename].append(value)
            #         # self.live_socket.set_point_now(codename, value)


def main():
    cc = CryostatController()
    # cm.dc_4_point_measurement(1e-6, 1e-4)
    cc.start()


if __name__ == '__main__':
    main()
