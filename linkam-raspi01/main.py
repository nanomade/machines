import time
import threading

from PyExpLabSys.common.sockets import DataPushSocket
from PyExpLabSys.common.sockets import DateDataPullSocket

# This is not very abstract, see inspiration on how to do this
# at the cryostat
# Soon we will also need constant-gate and thus will need to
# improve abstraction level
from linkam_one_shot_van_der_pauw import LinkamSweepedOneShotVDP


class LinkamController(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.quit = False
        self.lm = LinkamSweepedOneShotVDP()

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
            if element.get('measurement') == 'one_shot_vdp':
                self.start_one_shot_vdp(**element)

        elif cmd == 'abort':
            self.lm.abort_measurement()
            # print('Abort current measurement')
            # print('Currently measurement is:')
            # print(self.lm.current_measurement['type'])
            # print()
        else:
            print('Unknown command')

    def start_one_shot_vdp(  # Could this be just **kwargs?
            self, comment: str, v_low: float, v_high: float,
            compliance: float, total_steps: int,
            repeats: int, time_pr_step, end_wait: int, **kwargs
    ):
        """
        **kwargs is not actually used, but will eat keywords
        originating from the network syntax.
        """
        # TODO: Check that measurement is not already running
        t = threading.Thread(
            target=self.lm.one_shot_van_der_pauw,
            args=(  # Could this be just **kwargs
                comment,
                v_low,
                v_high,
                compliance,
                total_steps,
                repeats,
                time_pr_step,
                end_wait
            )
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

            lm = self.lm.current_measurement
            self.pullsocket.set_point_now('v_backgate', lm['v_backgate'])
            self.pullsocket.set_point_now('lock_in_v1', lm['lock_in_v1'])
            self.pullsocket.set_point_now('lock_in_v2', lm['lock_in_v2'])

            current_measurement = self.lm.current_measurement['type']
            if not current_measurement:
                current_measurement = 'Idle'
            self.pullsocket.set_point_now('status', current_measurement)
            print(self.lm.current_measurement['type'])


def main():
    lc = LinkamController()
    lc.start()


if __name__ == '__main__':
    main()