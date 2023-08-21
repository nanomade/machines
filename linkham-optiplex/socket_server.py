""" Flow control for analog MFCs"""
import json
import time
import socket
import threading

import nidaqmx
from nidaqmx.constants import TerminalConfiguration

import PyExpLabSys.auxiliary.pid as PID
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.sockets import DataPushSocket
from PyExpLabSys.common.sockets import DateDataPullSocket


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
        self.livesocket = LiveSocket('MFC_Flow_Linkam', socket_names,
                                     no_internal_data_pull_socket=True)
        self.livesocket.start()

        for device in devices.keys():
            self.set_flow(device, 0)

        self.pushsocket = DataPushSocket(name, action='enqueue')
        self.pushsocket.start()

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setblocking(0)

        self.pid = PID.PID(pid_p=5e-4, pid_i=4e-6, p_min=-0.5, p_max=5)
        self.pid_setpoint = None
        self.running = True

    def _read_h20_conc(self):
        cmd = 'h20_concentration_linkam#json'
        error = 0
        while -1 < error < 50:
            try:
                self.socket.sendto(cmd.encode(), ('10.54.4.56', 9001))
                time.sleep(0.01)
                recv = self.socket.recv(65535)
                error = -1
            except BlockingIOError:
                time.sleep(0.2)
                error += 1
                if error > 3:
                    print('Comm error, cannont read humidity')
        if error > -1:
            return -1
        try:
            data = json.loads(recv)
            value = data[1]
            concentration = float(value)
        except ValueError:
            concentration = -1
        return concentration

    def _read_all_flows(self):
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
            # print(name + ': ' + str(flow))
            self.pullsocket.set_point_now(name, flow)
            self.livesocket.set_point_now(name, flow)

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
        self.pullsocket.set_point_now(name, value)
        self.livesocket.set_point_now(name, value)
        return True

    def _calculate_wanted_flow(self):
        # Dry flow is set staticly, regulation is done via wet flow
        dry_flow = 10 + (100 - self.pid_setpoint / 100)
        if dry_flow > 100:
            dry_flow = 100
        elif dry_flow < 10:
            dry_flow = 10
        self.set_flow(device='dry', value=dry_flow)

        h20_conc = self._read_h20_conc()
        wanted_flow = self.pid.wanted_power(h20_conc) + 0.5
        p = self.pid.proportional_contribution()
        i = self.pid.integration_contribution()
        print('P: {:.2f}. I: {:.2f}. Tot: {:.2f}'.format(p, i, wanted_flow - 0.5))
        self.set_flow(device='wet', value=wanted_flow)
        return wanted_flow

    def run(self):
        while self.running:
            time.sleep(0.25)
            if self.pid_setpoint:
                self._calculate_wanted_flow()

            qsize = self.pushsocket.queue.qsize()
            while qsize > 0:
                element = self.pushsocket.queue.get()

                cmd = element['cmd']
                if cmd == 'set_flow':
                    # If a flow is set manually, the PID is turned off
                    device = element['device']
                    flow = element['value']
                    self.pid_setpoint = None
                    self.set_flow(device=device, value=flow)
                elif cmd == 'set_pid_setpoint':
                    setpoint = element['value']
                    self.pid_setpoint = setpoint
                    self.pid.update_setpoint(setpoint)
                qsize = self.pushsocket.queue.qsize()
                print('Queue: ' + str(qsize))
            self._read_all_flows()


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
