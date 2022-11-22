import json
import time
import socket
import threading
import PySimpleGUI as sg

SERVER_IP = '10.54.4.67'
MFCs = {
    '23006960': 'CH4',
    '23006959': 'Ar',
    '23006958': 'H2'
}


class FlowReader(threading.Thread):
    """ Network reader """
    def __init__(self, serials: list):
        threading.Thread.__init__(self)
        self.name = 'Flow reader'
        self.running = True
        self.updating = False

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(1)

        self.flow_values = {}
        self.serials = list(serials)
        for serial in serials:
            self.flow_values[serial] = (0, 0)
            self.flow_values[serial + '_setpoint'] = (0, 0)

    def update_setpoint(self, serial, value):
        self.updating = True
        command = {
            serial: float(value)
        }
        command_json = 'json_wn#' + json.dumps(command)
        print(command_json)
        self.sock.sendto(command_json.encode(), ('10.54.4.67', 8500))
        time.sleep(0.1)
        recv = self.sock.recv(65535)
        print(recv)
        self.updating = False

    def run(self):
        while self.running:
            time.sleep(1.0)
            while self.updating:
                time.sleep(0.1)
            sws = ['{}_setpoint'.format(serial) for serial in self.serials]
            for serial in self.serials + sws:
                cmd = '{}#json'.format(serial).encode()
                self.sock.sendto(cmd, (SERVER_IP, 9000))
                recv = self.sock.recv(65535)
                data = json.loads(recv)
                self.flow_values[serial] = (time.time(), data[1])


def main():
    fr = FlowReader(MFCs.keys())
    fr.start()

    # Todo: It should be possible to auto-generate some of this from MFCs
    layout = [
        [
            sg.Text("CH4", size=(5, 1)),
            sg.Input(key='CH4_setpoint', size=(5, 1)),
            sg.Text(key='CH4_value', size=(13, 1)),
            sg.Text(key='CH4_actual_setpoint', size=(16, 1))
        ],

        [
            sg.Text("Ar", size=(5, 1)),
            sg.Input(key='Ar_setpoint', size=(5, 1)),
            sg.Text(key='Ar_value', size=(13, 1)),
            sg.Text(key='Ar_actual_setpoint', size=(16, 1))
        ],

        [
            sg.Text("H2", size=(5, 1)),
            sg.Input(key='H2_setpoint', size=(5, 1)),
            sg.Text(key='H2_value', size=(13, 1)),
            sg.Text(key='H2_actual_setpoint', size=(16, 1))
        ],
        [sg.Text(size=(40, 1), key='-OUTPUT-')],
        [sg.Button('Ok'), sg.Button('Stop Flow'), sg.Button('Quit')],
    ]
    window = sg.Window('MFC Control', layout, finalize=True)

    time.sleep(0.1)

    running = True
    while running:
        event, values = window.read(timeout=100)
        if event == sg.WINDOW_CLOSED or event == 'Quit':
            running = False
            continue
        if event == 'Stop Flow':
            for serial in MFCs.keys():
                fr.update_setpoint(serial, 0)
            window['CH4_setpoint'].update('0')
            window['Ar_setpoint'].update('0')
            window['H2_setpoint'].update('0')
        if event == 'Ok':
            try:
                float(values['CH4_setpoint'])
            except ValueError:
                window['CH4_setpoint'].update('0')
            try:
                float(values['Ar_setpoint'])
            except ValueError:
                window['Ar_setpoint'].update('0')
            try:
                float(values['H2_setpoint'])
            except ValueError:
                window['H2_setpoint'].update('0')

            event, values = window.read(timeout=10)
            
            for serial, name in MFCs.items():
                label = '{}_setpoint'.format(name)
                setpoint = float(values[label])
                fr.update_setpoint(serial, setpoint)

        for key, value in MFCs.items():
            label = value + '_value'
            flow = fr.flow_values[key]
            if time.time() - flow[0] < 10:
                flow_str = '{:.2f}mL/min'.format(flow[1])
            else:
                flow_str = '-'

            actual_setpoint = fr.flow_values[key + '_setpoint']
            setpoint_str = 'Current SP: {:.2f}'.format(actual_setpoint[1])

            try:
                window[value + '_value'].update(flow_str)
                window[value + '_actual_setpoint'].update(setpoint_str)
            except RuntimeError:
                # App is shutting down
                pass

    window.close()
    fr.running = False


if __name__ == '__main__':
    main()
