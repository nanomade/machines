from PyQt5 import QtWidgets, QtCore, uic
# from pyqtgraph import PlotWidget
import pyqtgraph as pg

import sys
import time
import json
import socket

from random import randint

class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):        
        super(MainWindow, self).__init__(*args, **kwargs)

        self.write_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.write_socket.setblocking(0)
        
        self.read_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.read_socket.setblocking(0)
        self.read_socket_in_use = False

        self.t_start = time.time()
        
        #Load the UI Page
        uic.loadUi('4point_delta.ui', self)

        self.start_button.clicked.connect(self._start_measurement)
        self.abort_button.clicked.connect(self._abort_measurement)
        # self.vti_temp_setpoint.editingFinished.connect(self._klaf)
        # self.vti_temp_setpoint.valueChanged.connect(self._update_vti_temp)
        # self.b_field_setpoint.valueChanged.connect(self._update_b_field)
        
        self.status_plot.setBackground('w')
        # self.b_field_plot.setBackground('w')

        # self.x = list(range(100))  # 100 time points
        # self.y = [randint(0,100) for _ in range(100)]  # 100 data points
        self.status_plot_x = []
        self.status_plot_y = []
        
        pen = pg.mkPen(color=(255, 0, 0))
        self.status_plot_line = self.status_plot.plot(
            self.status_plot_x,
            self.status_plot_y, pen=pen
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

    def _write_socket(self, cmd):
        socket_cmd = 'json_wn#' + json.dumps(cmd)
        self.read_socket.sendto(socket_cmd.encode(), ('10.54.4.78', 8510))
        time.sleep(0.1)
        recv = self.read_socket.recv(65535).decode('ascii')
        print(recv)
        
    def _read_socket(self, cmd, port=9000):
        self.read_socket_in_use = True
        try:
            socket_cmd = cmd + '#json'
            self.read_socket.sendto(socket_cmd.encode(), ('10.54.4.78', port))
            time.sleep(0.1)
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

    def _start_measurement(self):
        self.status_plot_x = []
        self.status_plot_y = []

        current = self.current.value() / 1e6
        comment = self.comment.text()
        measure_time = self.measure_time.value()
        command = {
            'cmd': 'start_measurement',
            'measurement': 'delta_constant_current',
            'comment': comment,
            'current': current,
            'measure_time': measure_time,
        }
        self._write_socket(command)

    def _abort_measurement(self):
        command = {
            'cmd': 'abort',
        }
        self._write_socket(command)

    def update_plot_data(self):
        if not self.read_socket_in_use:
            print()

            sample_temp = self._read_socket('cryostat_sample_temperature')
            self.sample_temp_show.setText('{:.2f}K'.format(sample_temp))

            v_sample_point = self._read_socket('v_sample', 9002)
            print('v_sample', v_sample_point)

            if v_sample_point is not None:
                self.status_plot_x.append(v_sample_point[0])
                self.status_plot_y.append(v_sample_point[1])

            
            status = self._read_socket('status', 9002)
            print('status', status, type(status))
            measurement_type = status['type']
            print(measurement_type)
            
        self.status_plot_line.setData(self.status_plot_x, self.status_plot_y)


        

def main():
    app = QtWidgets.QApplication(sys.argv)
    main = MainWindow()
    main.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
