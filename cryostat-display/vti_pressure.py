import json
import time
import socket
import threading
import PySimpleGUI as sg

SERVER_IP = '10.54.4.78'


class CryostatReader(threading.Thread):
    """ Network reader """
    def __init__(self):
        threading.Thread.__init__(self)
        self.name = 'VTI reader'
        self.running = True

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

def main():
    cr = CryostatReader()
    cr.start()

    small_font = ("Arial", 45)
    large_font = ("Arial", 90)

    layout = [
        [
            sg.Text("Pressure / mbar:", size=(15, 1), font=large_font),
            sg.Text(key='cryostat_vti_pressure', size=(13, 1), font=large_font),
        ],

        [
            sg.Text("Temperature / K:", size=(15, 1), font=small_font),
            sg.Text(key='cryostat_vti_temperature', size=(13, 1), font=small_font),
        ],

        [sg.Text(size=(40, 1), key='-OUTPUT-')],
        [sg.Button('Quit')],
    ]
    window = sg.Window('VTI Pressure', layout, finalize=True)

    time.sleep(0.1)

    running = True
    while running:
        event, values = window.read(timeout=100)
        if event == sg.WINDOW_CLOSED or event == 'Quit':
            running = False
            continue

        for key, value in cr.values.items():
            try:
                if time.time() - value[0] < 3:
                    value_str = '{:.3f}'.format(value[1])
                else:
                    value_str = '-'
            except ValueError:
                value_str = '-'

            try:
                window[key].update(value_str)
            except RuntimeError:
                # App is shutting down
                pass

    window.close()
    cr.running = False


if __name__ == '__main__':
    main()
