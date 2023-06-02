from PyQt5 import QtWidgets, QtCore, uic
from PyQt5.QtWidgets import QMessageBox
# from PyQt5.QtWidgets import QTableWidgetItem

# from pyqtgraph import PlotWidget
import pyqtgraph as pg

import sys
import time
import json
import socket


class InvalidFieldError(Exception):
    pass


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        self.write_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.write_socket.setblocking(0)

        # Used for continous communication with cryostat
        self.read_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.read_socket.setblocking(0)
        self.read_socket_in_use = False

        self.t_start = time.time()
        uic.loadUi('cryostat_frontend.ui', self)

        self.vti_temp_setpoint.valueChanged.connect(self._update_vti_temp)
        self.sample_temp_setpoint.valueChanged.connect(self._update_sample_temp)
        self.b_field_setpoint.valueChanged.connect(self._update_b_field)

        self.activate_ramp_button.clicked.connect(self._activate_ramp)
        self.stop_ramp_button.clicked.connect(self._stop_ramp)

        self.start_4point_delta_button.clicked.connect(self._start_4point_delta)
        self.abort_measurement_button.clicked.connect(self._abort_measurement)

        self.temperature_plot.setBackground('w')
        self.b_field_plot.setBackground('w')
        self.status_plot.setBackground('w')

        self.vti_temp_x = []
        self.vti_temp_y = []
        self.sample_temp_x = []
        self.sample_temp_y = []
        self.b_field_x = []
        self.b_field_y = []

        self.ramp_start = 0
        self.ramp = None

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

    def alert(self, msg):
        box = QMessageBox()
        box.setIcon(QMessageBox.Critical)
        box.setText(msg)
        box.setWindowTitle(msg)
        box.exec_()
        
    def _read_field(self, x, y):
        """
        Read a specific field in the ramp table.
        If the field is empty None is returned.
        If the field cannot be read as float, an exception is raised
        """
        item = self.ramp_table.item(x, y)
        if item is None:
            return None
        if len(item.text()) == 0:
            return None
        try:
            value = float(item.text())
        except ValueError:
            self.alert('Value error in ramp')
            # msg = QMessageBox()
            # msg.setIcon(QMessageBox.Critical)
            # msg.setText('Value error in ramp')
            # msg.setWindowTitle("Error")
            # msg.exec_()
            value = None
            raise InvalidFieldError
        return value

    def _parse_ramp(self):
        ramp = []
        i = 0
        while i > -1:
            try:
                dt = self._read_field(i, 0)
                temp = self._read_field(i, 1)
                b_field = self._read_field(i, 2)
            except InvalidFieldError:
                return
            if None in (dt, temp, b_field):
                break

            ramp.append({'dt': dt, 'temp': temp, 'b_field': b_field})
            i = i + 1
        return ramp

    def _activate_ramp(self):
        self.ramp_start = time.time()
        ramp = self._parse_ramp()
        if ramp is not None:
            self.ramp = ramp

    def _stop_ramp(self):
        self.ramp_start = 0
        self.ramp = None

    def _write_socket(self, cmd, port=8500):
        socket_cmd = 'json_wn#' + json.dumps(cmd)
        self.read_socket.sendto(socket_cmd.encode(), ('10.54.4.78', port))
        time.sleep(0.1)
        recv = self.read_socket.recv(65535).decode('ascii')
        print(recv)

    def _update_via_socket(self, command, setpoint):
        command = {
            # 'cmd': 'vti_temperature_setpoint',
            'cmd': command,
            'setpoint': setpoint,
            'slope': 5  # K/min, so far hardcodet and not in use
        }
        self._write_socket(command)
        # todo: Check reply that command is acknowledged

    def _abort_measurement(self):
        command = {
            'cmd': 'abort',
        }
        self._write_socket(command, 8510)

    def _start_4point_delta(self):
        comment = self.measurement_comment.text()
        current = self.delta_4_point_current.value()
        measure_time = self.delta_4_point_measure_time.value()
        if len(comment) < 5:
            self.alert('Comment too short')
            return False

        command = {
            'cmd': 'start_measurement',
            'measurement': 'delta_constant_current',
            'comment': comment,
            'current': current,
            'measure_time': measure_time
        }
        print(command)
        # self._write_socket(command, 8510)
        
        
    def _update_vti_temp(self):
        setpoint = self.vti_temp_setpoint.value()
        self._update_via_socket('vti_temperature_setpoint', setpoint)

    def _update_b_field(self):
        setpoint = self.b_field_setpoint.value()
        self._update_via_socket('b_field_setpoint', setpoint)

    def _update_sample_temp(self):
        setpoint = self.sample_temp_setpoint.value()
        self._update_via_socket('sample_temperature_setpoint', setpoint)

    def _read_socket(self, cmd, port=9000):
        self.read_socket_in_use = True
        try:
            socket_cmd = cmd + '#json'
            self.read_socket.sendto(socket_cmd.encode(), ('10.54.4.78', port))
            time.sleep(0.01)
            recv = self.read_socket.recv(65535).decode('ascii')
            data = json.loads(recv)
            if 'OLD' in data:
                value = None
            else:
                value = data[1]
        except BlockingIOError:
            value = None
        self.read_socket_in_use = False
        return value

    def update_plot_data(self):
        if self.ramp_start > 0:
            current_ramp_time = time.time() - self.ramp_start
            msg = '{:.1f}s ({:.2f}min)'
            self.ramp_time_show.setText(
                msg.format(current_ramp_time, current_ramp_time/60.0)
            )
            ramp_time_sum = 0
            ramp_line = 0
            for row in self.ramp:
                dt = row['dt'] * 60
                if ramp_time_sum + dt < current_ramp_time:
                    ramp_time_sum += dt
                    ramp_line += 1
                else:
                    break
            if not row['temp'] == self.sample_temp_setpoint.value():
                self.sample_temp_setpoint.setValue(row['temp'])
            if not row['b_field'] == self.b_field_setpoint.value():
                self.b_field_setpoint.setValue(row['b_field'])

            # Highlight current ramp line:
            self.ramp_table.selectRow(ramp_line)
        else:
            self.ramp_time_show.setText('')

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

            # Read status of ongoing measurement
            status = self._read_socket('status', 9002)
            print('status', status, type(status))
            measurement_type = status['type']
            print(measurement_type)

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
