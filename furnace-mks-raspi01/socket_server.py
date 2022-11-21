""" Flow control for ??? furnace MKS MFCs """
import threading
import time
import PyExpLabSys.drivers.mks_g_series as mks_g_series
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import DataPushSocket
# from PyExpLabSys.common.sockets import LiveSocket


class FlowControl(threading.Thread):
    """ Keep updated values of the current flow """
    def __init__(self, mks_instance, mfcs, devices, name):
        threading.Thread.__init__(self)
        self.mfcs = mfcs
        self.mks = mks_instance

        socket_names = []
        timeouts = []
        for device in devices:
            socket_names.append(device)
            socket_names.append(device + '_setpoint')
            timeouts.append(3.0)
            timeouts.append(1e9)

        self.pullsocket = DateDataPullSocket(
            name,
            socket_names,
            timeouts=timeouts,
            port=9000
        )
        self.pullsocket.start()
        for device in devices:
            addr = self.mfcs[device]
            setpoint = self.mks.read_setpoint(addr)
            self.pullsocket.set_point_now(device + '_setpoint', setpoint)

        self.pushsocket = DataPushSocket(name, action='enqueue')
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
                mfc = list(element.keys())[0]
                print(element[mfc])
                print('Queue: ' + str(qsize))
                self.mks.set_flow(value=element[mfc], addr=self.mfcs[mfc])
                self.pullsocket.set_point_now(mfc + '_setpoint', element[mfc])
                qsize = self.pushsocket.queue.qsize()

            print('')
            for mfc in self.mfcs:
                flow = self.mks.read_flow(self.mfcs[mfc])
                print(mfc + ': ' + str(flow))
                self.pullsocket.set_point_now(mfc, flow)
                # self.livesocket.set_point_now(mfc, flow)


# TODO! Consider to expand the driver and add some diagnostics, eg. temperatures
# valve opening or what else can be read from the rs485 interface
def main():
    """ Main function """
    port = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_AU05DDV3-if00-port0'
    devices = ['23006960', '23006959', '23006958']
    name = 'furnace_mks_mfc_control'

    i = 0
    mfcs = {}
    mks = mks_g_series.MksGSeries(port=port)
    for i in range(1, 4):
        time.sleep(2)
        print('!')
        serial = mks.read_serial_number(i)
        print(serial)
        if serial in devices:
            mfcs[serial] = i

    flow_control = FlowControl(mks, mfcs, devices, name)
    flow_control.start()

    while True:
        time.sleep(2)


if __name__ == '__main__':
    main()
