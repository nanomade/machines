from PyQt5 import QtGui, QtWidgets, QtCore, uic
from PyQt5.QtWidgets import QMessageBox
import pyqtgraph as pg

import sys  # why?
import time

from collections import deque

from read_deflection_stream import DeflectionReader
from save_deflection_stream import DeflectionSaver


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        # When measurement is running, data is pulled from deflection_saver
        # when not running, it is taken directly from DeflectionReader()
        self.deflection_saver = None
        self.reader = DeflectionReader()
        self.reader.start()
        time.sleep(1)

        self.t_start = time.time()
        uic.loadUi('deflection_sensor.ui', self)

        self.start_recording_pushButton.clicked.connect(self._start_measurement)
        self.stop_recording_pushButton.clicked.connect(self._stop_measurement)

        self.reset_plot_data()
        self.recording_started = None

        self.pressure_plot.setBackground('w')
        pen = pg.mkPen(color=(255, 0, 0), width=5)
        self.pressure_line = self.pressure_plot.plot(
            self.pressure_x, self.pressure_y, pen=pen
        )

        font = QtGui.QFont()
        font.setPixelSize(30)
        self.pressure_plot.getAxis("left").setStyle(tickFont=font)
        self.pressure_plot.getAxis("bottom").setStyle(tickFont=font)

        self.pressure_plot.setTitle('Pressure', color='k', size='30pt')
        self.timer = QtCore.QTimer()
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.update_plot_data)
        self.timer.start()

    def reset_plot_data(self):
        self.pressure_x = deque([], maxlen=1000)
        self.pressure_y = deque([], maxlen=1000)
        self.temperature_x = deque([], maxlen=1000)
        self.temperature_y = deque([], maxlen=1000)

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

        self.reader.stop()
        self.reader = None
        self.reset_plot_data()
        self.recording_started = time.time()
        self.deflection_saver = DeflectionSaver()
        self.deflection_saver.infinite_recording(comment)

    def _stop_measurement(self):
        if self.deflection_saver is not None:
            self.deflection_saver.stop_recording()
            time.sleep(0.2)
            self.deflection_saver = None
        self.reset_plot_data()
        self.recording_started = None
        if self.reader is None:
            self.reader = DeflectionReader()
            self.reader.start()

    def closeEvent(self, *args):
        # Args contains an event from qt, currently not used for anything
        if self.reader is not None:
            self.reader.stop()
        if self.deflection_saver is not None:
            self.deflection_saver.stop_measurement()

    def update_plot_data(self):
        if self.reader is not None:
            data = self.reader.return_data()
        else:
            data = self.deflection_saver.data

        if data is None:
            return

        pressure = data['p']
        temperature = data['t']
        ref_pressure = data['p_ref']
        ref_temperature = data['t_ref']

        self.pressure_show.setText('{}Pa'.format(pressure))
        self.temperature_show.setText('{:.2f}C'.format(temperature))
        self.ref_pressure_show.setText('{}Pa'.format(ref_pressure))
        self.ref_temperature_show.setText('{:.2f}C'.format(ref_temperature))
        self.delta_p_show.setText('{}Pa'.format(pressure - ref_pressure))
        if self.recording_started is not None:
            recording_time = '{:.0f}s'.format(time.time() - self.recording_started)
        else:
            recording_time = '-'
        self.recording_time_show.setText(recording_time)

        self.pressure_x.append(time.time() - self.t_start)
        self.pressure_y.append(pressure)

        self.temperature_x.append(time.time() - self.t_start)
        self.temperature_y.append(temperature)

        self.pressure_line.setData(self.pressure_x, self.pressure_y)


def main():
    app = QtWidgets.QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
