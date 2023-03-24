""" Flow control for analog MFCs"""
import time
import threading

import nidaqmx
from nidaqmx.constants import TerminalConfiguration

from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import DataPushSocket
# from PyExpLabSys.common.sockets import LiveSocket


class FlowControl(threading.Thread):
    """ Keep updated values of the current flow """
    def __init__(self, devices, name):
        threading.Thread.__init__(self)
        socket_names = []
        timeouts = []
        self.devices = devices
        for device in devices.keys():
            name = 'mfc_flow_{}_linkham'.format(device)
            name_setpoint = 'mfc_flow_{}_setpoint_linkham'.format(device)
            socket_names.append(name)
            socket_names.append(name_setpoint)
            timeouts.append(3.0)
            timeouts.append(1e9)

        self.pullsocket = DateDataPullSocket(
            name,
            socket_names,
            timeouts=timeouts,
            port=9000
        )
        self.pullsocket.start()

        for device in devices.keys():
            self.set_flow(device, 0)

        self.pushsocket = DataPushSocket(name, action='enqueue')
        self.pushsocket.start()

        # self.livesocket = LiveSocket('linkham_mfc_flows', devices)
        # self.livesocket.start()
        self.running = True

    def read_all_flows(self):
        with nidaqmx.Task() as task:
            # Add all channels to task
            for mfc_info in self.devices.values():
                channel = mfc_info['channel']
                name = 'Dev1/ai{}'.format(channel)
                task.ai_channels.add_ai_voltage_chan(
                    name, terminal_config=TerminalConfiguration.RSE
                )
            values = task.read()

        # Values are now actual read values in same order is given
        # in self.devices
        for i in range(0, len(self.devices)):
            flow_raw = values[i]
            device = list(self.devices.keys())[i]
            flow_range = self.devices[device]['range']
            flow = flow_raw * flow_range / 5.0

            name = 'mfc_flow_{}_linkham'.format(device)
            print(name + ': ' + str(flow))
            self.pullsocket.set_point_now(name, flow)
            # self.livesocket.set_point_now(mfc, flow)

    def set_flow(self, device, value):
        # Actual update of analog out
        channel = self.devices[device]['channel']
        flow_range = self.devices[device]['range']
        voltage = 5 * value / flow_range

        name = 'Dev1/ao{}'.format(channel)
        with nidaqmx.Task() as task:
            task.ao_channels.add_ao_voltage_chan(name)
            task.write([voltage], auto_start=True)

        # Update of setpoint book-keeping
        name = 'mfc_flow_{}_setpoint_linkham'.format(device)
        self.pullsocket.set_point_now(name, 0)
        return True

    def run(self):
        while self.running:
            time.sleep(0.25)
            qsize = self.pushsocket.queue.qsize()
            while qsize > 0:
                element = self.pushsocket.queue.get()
                # cmd is not currently actually used - could be used for
                # fancier stuff, like asking for a ramp or similar
                # cmd = element['cmd']
                device = element['device']
                flow = element['value']
                print('Queue: ' + str(qsize))
                self.set_flow(device=device, value=flow)
                qsize = self.pushsocket.queue.qsize()
            print('')
            self.read_all_flows()


def main():
    """ Main function """
    devices = {
        # Range in mL/min. Analog range is assumed 0-5V
        'wet': {'channel': 0, 'range': 5},
        'dry': {'channel': 1, 'range': 100},
    }
    name = 'linkham_mfc_control'

    flow_control = FlowControl(devices, name)
    flow_control.start()

    while True:
        time.sleep(2)


if __name__ == '__main__':
    main()
