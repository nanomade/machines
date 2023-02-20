import time
import threading

from PyExpLabSys.common.sockets import DataPushSocket
from PyExpLabSys.common.sockets import DateDataPullSocket

from linkam_sweeped_one_shot_vdp import LinkamSweepedOneShotVDP
from linkam_constant_gate_one_shot_vdp import LinkamConstantGateVDP


class LinkamController(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.quit = False
        # Default to Sweeped One Shot
        self.measurement = LinkamSweepedOneShotVDP()

        self.pushsocket = DataPushSocket('Linkam', action='enqueue')
        self.pushsocket.start()

        self.pullsocket = DateDataPullSocket(
            'linkam', ['status', 'lock_in_v1', 'lock_in_v2', 'v_backgate'],
            timeouts=[999999, 30, 30, 30], port=9000
        )
        self.pullsocket.start()

    def _handle_element(self, element):
        cmd = element.get('cmd')
        if cmd == 'start_measurement':
            print(element.get('measurement'))
            if element.get('measurement') == 'sweeped_one_shot_vdp':
                self.start_sweeped_one_shot_vdp(**element)
            elif element.get('measurement') == 'constant_gate_one_shot_vdp':
                self.start_constant_gate_one_shot_vdp(**element)

        elif cmd == 'abort':
            self.measurement.abort_measurement()
            # print('Abort current measurement')
            # print('Currently measurement is:')
            # print(self.lm.current_measurement['type'])
            # print()
        else:
            print('Unknown command')

    def constant_gate_one_shot_vdp(self, **kwargs):
        """
        Start the sweeped Van der Pauw measurement
        Arguments are fed directly from the udp socket, we could consider to do a
        verification step and report error rather than crash on missing arguments.
        """
        # TODO: Check that measurement is not already running
        self.measurement = LinkamConstantGateVDP()
        t = threading.Thread(
            target=self.measurement.constant_gate_one_shot_vdp,
            kwargs=kwargs,
        )
        t.start()
        return True

    def run(self):
        while not self.quit:
            time.sleep(1)
            print('Running')
            qsize = self.pushsocket.queue.qsize()
            while qsize > 0:
                element = self.pushsocket.queue.get()
                qsize = self.pushsocket.queue.qsize()
                self._handle_element(element)

            meas = self.measurement.current_measurement
            self.pullsocket.set_point_now('v_backgate', meas['v_backgate'])
            self.pullsocket.set_point_now('lock_in_v1', meas['lock_in_v1'])
            self.pullsocket.set_point_now('lock_in_v2', meas['lock_in_v2'])

            current_measurement = self.measurement.current_measurement['type']
            if not current_measurement:
                current_measurement = 'Idle'
            self.pullsocket.set_point_now('status', current_measurement)
            print(self.measurement.current_measurement['type'])


def main():
    lc = LinkamController()
    lc.start()


if __name__ == '__main__':
    main()
