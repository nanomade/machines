from PyQt5 import QtGui, QtWidgets, QtCore, uic
from PyQt5.QtWidgets import QMessageBox
import pyqtgraph as pg

import sys
import json
import time
import socket
import threading

from collections import deque


SERVER_IP = "10.54.4.254"


class NoiseSpectrumControl(threading.Thread):
    """Network reader"""

    def __init__(self):
        threading.Thread.__init__(self)
        self.name = "NoiseSpectrumControl"
        self.running = True
        self.daemon = True

        # # If we want to start a measurement, we put it here
        self.next_command = None

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(1)
        self.sock.settimeout(1)

        self.measurement_running = None
        self.current_data = None

    def prepare_next_command(self, command):
        # An actual command will only be accepted if no measurement is running.
        # An abort will be accepted only if the measurent is running.
        command_accepted = False
        if self.measurement_running is None:
            # We do not have contact to backend
            pass
        if command["cmd"] == "start_measurement":
            if not self.measurement_running:
                command_accepted = True
                self.next_command = command
        elif command["cmd"] == "abort":
            if self.measurement_running:
                command_accepted = True
                self.next_command = command
        return command_accepted

    def run(self):
        while self.running:
            time.sleep(1.0)
            if self.next_command is not None:
                socket_command = "json_wn#" + json.dumps(self.next_command)
                self.next_command = None
                self.sock.sendto(socket_command.encode(), (SERVER_IP, 8500))
                time.sleep(0.01)
                recv = self.sock.recv(65535)
                print(recv)
            try:
                self.sock.sendto(b"measurement_running#json", (SERVER_IP, 9000))
                recv = self.sock.recv(65535)
                data = json.loads(recv)
                self.measurement_running = data[1]
            except socket.timeout:
                self.measurement_running = None

            try:
                self.sock.sendto(b"current_data#json", (SERVER_IP, 9000))
                recv = self.sock.recv(65535)
                data = json.loads(recv)
                self.current_data = data
            except socket.timeout:
                self.current_data = None


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        self.reader = NoiseSpectrumControl()
        self.reader.start()
        time.sleep(1)

        uic.loadUi("spectrum_control.ui", self)

        self.noise_spectrum_pushButton.clicked.connect(self._start_measurement)
        self.constant_frequency_pushButton.clicked.connect(self._start_measurement)
        self.sweepd_xy_spectrum_pushButton.clicked.connect(self._start_measurement)
        self.abort_pushButton.clicked.connect(self._abort)

        self.data_plot.setBackground("w")
        self.t_start = time.time()
        self.data_plot_x = deque([], maxlen=500)
        self.data_plot_y = deque([], maxlen=500)

        pen = pg.mkPen(color=(255, 0, 0), width=5)
        self.data_plot_line = self.data_plot.plot(
            self.data_plot_x, self.data_plot_y, pen=pen
        )

        font = QtGui.QFont()
        font.setPixelSize(30)
        self.data_plot.getAxis("left").setStyle(tickFont=font)
        self.data_plot.getAxis("bottom").setStyle(tickFont=font)
        # self.data_plot.setTitle('Data', color='k', size='30pt')

        self.timer = QtCore.QTimer()
        self.timer.setInterval(750)
        self.timer.timeout.connect(self.update_data)
        self.timer.start()

    def alert(self, msg):
        box = QMessageBox()
        box.setIcon(QMessageBox.Critical)
        box.setText(msg)
        box.setWindowTitle(msg)
        box.exec_()

    def _start_measurement(self):
        comment = self.comment_lineEdit.text()
        if len(comment) < 5:
            self.alert("Comment too short")
            return False

        # Clear plot when starting a measurement
        self.t_start = time.time()
        self.data_plot_x = deque([], maxlen=500)
        self.data_plot_y = deque([], maxlen=500)

        command = {"cmd": "start_measurement", "comment": comment}
        sender = self.sender().text()
        log_steps = self.log_steps_checkBox.checkState() > 0
        if sender == "Noise Spectrum":
            params = {
                "measurement": "record_noise_spectrum",
                "high": self.frequency_high.value(),
                "low": self.frequency_low.value(),
                "steps": self.frequency_steps.value(),
                "log_scale": log_steps,
            }
        if sender == "Constant Frequency":
            params = {
                "measurement": "record_xy_spectrum",
                "freq_high": self.frequency_high.value(),
                "freq_low": self.frequency_low.value(),
                "acquisition_time": self.step_time.value(),
            }
        if sender == "Sweeped XY Spectrum":
            params = {
                "measurement": "record_sweeped_xy_measurement",
                "high": self.frequency_high.value(),
                "low": self.frequency_low.value(),
                "steps": self.frequency_steps.value(),
                "time_pr_step": self.step_time.value(),
                "log_scale": log_steps,
            }
        command.update(params)
        print(command)
        self.reader.prepare_next_command(command)

    def _abort(self):
        command = {
            "cmd": "abort",
        }
        print(command)
        self.reader.prepare_next_command(command)

    def update_data(self):
        if self.reader.measurement_running is None:
            msg = "Not connected to backend"
        elif self.reader.measurement_running:
            msg = "Measurement running"
        else:
            msg = "Measurement not running"
        self.data_plot_x.append(time.time() - self.t_start)
        self.data_plot_y.append(self.reader.current_data[1]["x"])
        self.measurement_running_label.setText(msg)

        x_str = "{:.4f}".format(self.reader.current_data[1]["x"] * 1000)
        y_str = "{:.4f}".format(self.reader.current_data[1]["y"] * 1000)
        freq_str = "{:.2f}".format(self.reader.current_data[1]["freq"])
        self.x_value_show.setText(x_str)
        self.y_value_show.setText(y_str)
        self.freq_value_show.setText(freq_str)

        self.data_plot_line.setData(self.data_plot_x, self.data_plot_y)


def main():
    app = QtWidgets.QApplication(sys.argv)
    main = MainWindow()
    main.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
