from PyQt5 import QtWidgets, QtCore, uic
# from pyqtgraph import PlotWidget
import pyqtgraph as pg

import sys
import time
import json
import socket


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        self.write_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.write_socket.setblocking(0)

        self.read_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.read_socket.setblocking(0)
        self.read_socket_in_use = False

        self.t_start = time.time()
        uic.loadUi('cryostat_frontend.ui', self)

        # self.vti_temp_setpoint.editingFinished.connect(self._klaf)
        self.vti_temp_setpoint.valueChanged.connect(self._update_vti_temp)
        self.b_field_setpoint.valueChanged.connect(self._update_b_field)

        self.temperature_plot.setBackground('w')
        self.b_field_plot.setBackground('w')

        # self.x = list(range(100))  # 100 time points
        # self.y = [randint(0,100) for _ in range(100)]  # 100 data points
        self.vti_temp_x = []
        self.vti_temp_y = []
        self.sample_temp_x = []
        self.sample_temp_y = []
        self.b_field_x = []
        self.b_field_y = []

        pen = pg.mkPen(color=(255, 0, 0))
        pen2 = pg.mkPen(color=(0, 0, 255))
        self.vti_temp_line = self.temperature_plot.plot(
            self.vti_temp_x,
            self.vti_temp_y, pen=pen
        )
        self.sample_temp_line = self.temperature_plot.plot(
            self.sample_temp_x,
            self.sample_temp_y, pen=pen2
        )
        self.b_field_line = self.b_field_plot.plot(
            self.vti_temp_x,
            self.vti_temp_y, pen=pen
        )

        self.timer = QtCore.QTimer()
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.update_plot_data)
        self.timer.start()

    def _update_vti_temp(self):
        setpoint = self.vti_temp_setpoint.value()
        command = {
            'cmd': 'vti_temperature_setpoint',
            'setpoint': setpoint,
            'slope': 5  # K/min, so far hardcodet and not in use
        }
        self._write_socket(command)

    def _update_b_field(self):
        setpoint = self.b_field_setpoint.value()
        command = {
            'cmd': 'b_field_setpoint',
            'setpoint': setpoint,
            'slope': 5  # K/min, so far hardcodet and not in use
        }
        self._write_socket(command)

    # def _update_sample_temp(self):
    #     setpoint = self.
    #     command = {
    #         # If target is 0 heater is turned off
    #         'cmd': 'sample_temperature_setpoint',
    #         'setpoint': 1,  # K
    #         'slope': 5  # K/min, so far hardcodet and not in use
    #     }
    #     print(command)

    def _write_socket(self, cmd):
        socket_cmd = 'json_wn#' + json.dumps(cmd)
        self.read_socket.sendto(socket_cmd.encode(), ('10.54.4.78', 8500))
        time.sleep(0.01)
        recv = self.read_socket.recv(65535).decode('ascii')
        print(recv)

    def _read_socket(self, cmd):
        self.read_socket_in_use = True
        try:
            socket_cmd = cmd + '#json'
            self.read_socket.sendto(socket_cmd.encode(), ('10.54.4.78', 9000))
            time.sleep(0.01)
            recv = self.read_socket.recv(65535).decode('ascii')
            data = json.loads(recv)
            value = data[1]
        except BlockingIOError:
            value = None
        self.read_socket_in_use = False
        return value

    def update_plot_data(self):
        if not self.read_socket_in_use:
            vti_temp = self._read_socket('cryostat_vti_temperature')
            sample_temp = self._read_socket('cryostat_sample_temperature')
            b_field = self._read_socket('cryostat_magnetic_field')
            if vti_temp is None or b_field is None:
                return

            self.sample_temp_show.setText('{:.2f}K'.format(sample_temp))
            self.vti_temp_show.setText('{:.2f}K'.format(vti_temp))
            self.b_field_show.setText('{:.6f}T'.format(b_field))

            self.vti_temp_x.append(time.time() - self.t_start)
            self.vti_temp_y.append(vti_temp)
            self.sample_temp_x.append(time.time() - self.t_start)
            self.sample_temp_y.append(sample_temp)

            self.b_field_x.append(time.time() - self.t_start)
            self.b_field_y.append(b_field)

        self.vti_temp_line.setData(self.vti_temp_x, self.vti_temp_y)
        self.sample_temp_line.setData(self.sample_temp_x, self.sample_temp_y)
        self.b_field_line.setData(self.b_field_x, self.b_field_y)


def main():
    app = QtWidgets.QApplication(sys.argv)
    main = MainWindow()
    main.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
