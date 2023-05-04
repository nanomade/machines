from PyQt5 import QtGui, QtWidgets, QtCore, uic
# from pyqtgraph import PlotWidget
import pyqtgraph as pg

import sys  # why?
import json
import time
import socket
import threading

from collections import deque


SERVER_IP = '10.54.4.78'


class CryostatReader(threading.Thread):
    """ Network reader """
    def __init__(self):
        threading.Thread.__init__(self)
        self.name = 'VTI reader'
        self.running = True
        self.daemon = True

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(1)
        self.sock.settimeout(1)
        self.values = {
            'cryostat_vti_pressure': (-1, -1),
            'cryostat_vti_temperature': (-1, -1),
        }

    def run(self):
        while self.running:
            time.sleep(1.0)
            for codename in self.values.keys():
                try:
                    cmd = '{}#json'.format(codename).encode()
                    self.sock.sendto(cmd, (SERVER_IP, 9000))
                    print('klaf', codename, time.time())
                    recv = self.sock.recv(65535)
                    data = json.loads(recv)
                    self.values[codename] = (time.time(), data[1])
                except socket.timeout:
                    print('Timeout')
                    time.sleep(1)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        self.reader = CryostatReader()
        self.reader.start()
        time.sleep(1)

        self.t_start = time.time()
        uic.loadUi('cryostat_data_display.ui', self)

        self.vti_pressure_plot.setBackground('w')
        self.vti_pressure_x = deque([], maxlen=100)
        self.vti_pressure_y = deque([], maxlen=100)

        pen = pg.mkPen(color=(255, 0, 0), width=5)
        self.vti_pressure_line = self.vti_pressure_plot.plot(
            self.vti_pressure_x, self.vti_pressure_y, pen=pen
        )

        font = QtGui.QFont()
        font.setPixelSize(30)
        self.vti_pressure_plot.getAxis("left").setStyle(tickFont=font)
        self.vti_pressure_plot.getAxis("bottom").setStyle(tickFont=font)

        self.vti_pressure_plot.setTitle('Temperature', color='k', size='30pt')
        self.timer = QtCore.QTimer()
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.update_plot_data)
        self.timer.start()

    def update_plot_data(self):
        vti_temp = self.reader.values['cryostat_vti_temperature'][1]
        vti_pressure = self.reader.values['cryostat_vti_pressure'][1]

        self.vti_temp_show.setText('{:.2f}K'.format(vti_temp))
        self.vti_pressure_show.setText('{:.3f}mbar'.format(vti_pressure))

        self.vti_pressure_x.append(time.time() - self.t_start)
        self.vti_pressure_y.append(vti_pressure)

        self.vti_pressure_line.setData(self.vti_pressure_x, self.vti_pressure_y)


def main():
    app = QtWidgets.QApplication(sys.argv)
    main = MainWindow()
    main.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
