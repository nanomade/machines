""" Remote control for Noise Spectrum measurement """
import threading
import time
from record_spectrum import NoiseSpectrumRecorder
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import DataPushSocket
# from PyExpLabSys.common.sockets import LiveSocket


class NoiseSpectrumRecorderControl(threading.Thread):
    """ Keep updated values of the current flow """
    def __init__(self):
        threading.Thread.__init__(self)
        self.nsr = NoiseSpectrumRecorder()
        # socket_names = []
        # timeouts = []
        # for device in devices:
        #     socket_names.append(device)
        #     socket_names.append(device + '_setpoint')
        #     timeouts.append(3.0)
        #     timeouts.append(1e9)

        # self.pullsocket = DateDataPullSocket(
        #     name,
        #     socket_names,
        #     timeouts=timeouts,
        #     port=9000
        # )
        # self.pullsocket.start()
        # for device in devices:
        #     addr = self.mfcs[device]
        #     setpoint = self.mks.read_setpoint(addr)
        #     self.pullsocket.set_point_now(device + '_setpoint', setpoint)

        self.pushsocket = DataPushSocket('NoiseSpectrumRecorder', action='enqueue')
        self.pushsocket.start()

        # self.livesocket = LiveSocket('furnace_mks_flows', devices)
        # self.livesocket.start()
        self.running = True

    def run(self):
        while self.running:
            time.sleep(0.1)
            qsize = self.pushsocket.queue.qsize()
            while qsize > 0:
                element = self.pushsocket.queue.get()
                # cmd = list(element.keys())[0]
                cmd = element['cmd']
                if cmd == 'start_measurement':
                    comment = element.get('comment', '-')
                    # print('Start measurement')
                    measurement = element['measurement']
                    if measurement == 'record_noise_spectrum':
                        print('Record Noise Spectrum')
                        t = threading.Thread(
                            target=self.nsr.record_spectrum,
                            args=(comment,)
                        )
                        t.start()

                    elif measurement == 'record_xy_spectrum':
                        print('Record XY spectrum')
                    elif measurement == 'record_sweeped_xy_measurement':
                        print('Record Sweeped XY measurement')

                if cmd == 'abort':
                    self.nsr.abort_measurement()
                print('Queue: ' + str(qsize))
                # self.mks.set_flow(value=element[mfc], addr=self.mfcs[mfc])
                # self.pullsocket.set_point_now(mfc + '_setpoint', element[mfc])
                qsize = self.pushsocket.queue.qsize()

            # print('')
            # for mfc in self.mfcs:
            #     flow = self.mks.read_flow(self.mfcs[mfc])
            #     print(mfc + ': ' + str(flow))
            #     self.pullsocket.set_point_now(mfc, flow)
            #     # self.livesocket.set_point_now(mfc, flow)


def main():
    """ Main function """
    nsr_control = NoiseSpectrumRecorderControl()
    nsr_control.start()

    while True:
        time.sleep(2)


if __name__ == '__main__':
    main()
