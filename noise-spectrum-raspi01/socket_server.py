""" Remote control for Noise Spectrum measurement """
import threading
import time
from record_spectrum import NoiseSpectrumRecorder
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import DataPushSocket

# from PyExpLabSys.common.sockets import LiveSocket


class NoiseSpectrumRecorderControl(threading.Thread):
    """Keep updated values of the current data"""

    def __init__(self):
        threading.Thread.__init__(self)
        self.nsr = NoiseSpectrumRecorder()

        # Consider to also add current measurement type
        socket_names = ['current_data', 'measurement_running']
        timeouts = [5, 1e6]

        self.pullsocket = DateDataPullSocket(
            'NoiseReaderControl', socket_names, timeouts=timeouts, port=9000
        )
        self.pullsocket.start()
        self.pushsocket = DataPushSocket('NoiseSpectrumRecorder', action='enqueue')
        self.pushsocket.start()

        # self.livesocket = LiveSocket('NoiseSpectrumRecorder', socket_names)
        # self.livesocket.start()
        self.running = True

    def _start_measurement(self, element):
        comment = element.get('comment', '-')
        print('Start measurement')
        measurement = element['measurement']

        if measurement == 'record_noise_spectrum':
            print('Noise Spectrum. Element is: ', element)
            t = threading.Thread(target=self.nsr.record_spectrum, kwargs=element)
            t.start()

        elif measurement == 'record_xy_spectrum':
            print('XY spectrum. Element is: ', element)
            t = threading.Thread(target=self.nsr.record_xy_measurement, kwargs=element)
            t.start()

        elif measurement == 'record_sweeped_xy_measurement':
            print('Sweeped XY. Element is: ', element)
            t = threading.Thread(
                target=self.nsr.record_sweeped_xy_measurement, kwargs=element
            )
            t.start()

    def run(self):
        while self.running:
            time.sleep(0.5)
            # If want a live-socket, set here as well
            self.pullsocket.set_point_now(
                'measurement_running', self.nsr.measurement_running
            )
            current_data = self.nsr.read_current_data()
            print('Current data ', current_data)
            self.pullsocket.set_point_now('current_data', current_data)

            qsize = self.pushsocket.queue.qsize()
            while qsize > 0:
                element = self.pushsocket.queue.get()
                cmd = element['cmd']
                if cmd == 'abort':
                    self.nsr.abort_measurement()
                if cmd == 'start_measurement':
                    self._start_measurement(element)
                qsize = self.pushsocket.queue.qsize()
                print('Queue: ' + str(qsize))


def main():
    """Main function"""
    nsr_control = NoiseSpectrumRecorderControl()
    nsr_control.start()

    while True:
        time.sleep(2)


if __name__ == '__main__':
    main()
