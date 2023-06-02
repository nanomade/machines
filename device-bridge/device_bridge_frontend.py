from PyQt5 import QtWidgets, QtCore, uic
# from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QMessageBox, QListWidgetItem
# from PyQt5.QtWidgets import QTableWidgetItem

# from pyqtgraph import PlotWidget
import pyqtgraph as pg

import sys
import time
import json
import socket


DEVICE_BRIDGE = '10.54.4.88'

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        self.read_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.read_socket.setblocking(0)

        uic.loadUi('device_bridge_frontend.ui', self)

        # self.vti_temp_setpoint.valueChanged.connect(self._update_vti_temp)
        # self.activate_ramp_button.clicked.connect(self._activate_ramp)

        self.live_plot.setBackground('w')

        self.live_plot_data = {'x': [], 'y': []}
        # self.live_plot_x = []
        # self.live_plot_y = []

        self.latest_values_items = {}
        self.latest_values_list.itemDoubleClicked.connect(self._on_clicked_list_item)
        self.focus_item = None
        
        pen = pg.mkPen(color=(255, 0, 0))
        self.live_plot_line = self.live_plot.plot([], [], pen=pen)

        self.timer = QtCore.QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.update)
        self.timer.start()

    def _read_socket(self, cmd):
        try:
            socket_cmd = cmd + '#json'
            self.read_socket.sendto(socket_cmd.encode(), (DEVICE_BRIDGE, 9000))
            time.sleep(0.05)
            recv = self.read_socket.recv(65535).decode('ascii')
            data = json.loads(recv)
            if 'OLD' in data:
                value = None
            else:
                value = data[1]
        except BlockingIOError:
            value = None
        return value

    def _on_clicked_list_item(self, item):
        print('Setting focus item to: {}'.format(item.text()))
        # self.focus_item = item.text()
        self.focus_item = item
        print(type(item))
        self.live_plot_data = {'x': [], 'y': []}        

    def update(self):
        qsize = self._read_socket('qsize')
        self.queue_size_show.setText('{}'.format(qsize))

        dead = self._read_socket('dead')
        alive = self._read_socket('alive')
        
        latest_values_raw = self._read_socket('latest_values')
        latest_values_dict = latest_values_raw
        for key, value  in latest_values_dict.items():
            if not key in self.latest_values_items:
                item = QListWidgetItem(key)
                self.latest_values_items[key] = item
                self.latest_values_list.addItem(item)
            
            if self.latest_values_items[key] == self.focus_item:
                try:
                    self.live_plot_data['x'].append(value[1])
                    self.live_plot_data['y'].append(value[0])
                except TypeError:
                    pass
            
            try:
                msg = '{}: {:.2f}'.format(key, value[0])
                self.latest_values_items[key].setText(msg)
            except TypeError:
                pass
                
        if len(self.live_plot_data['x']) > 1:
            # There you have it, a list comprehension!
            x = [x - self.live_plot_data['x'][0] for x in self.live_plot_data['x']]
            self.live_plot_line.setData(x, self.live_plot_data['y'])


def main():
    app = QtWidgets.QApplication(sys.argv)
    main = MainWindow()
    main.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
