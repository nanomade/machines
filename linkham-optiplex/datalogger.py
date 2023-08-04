""" UDP Value logger """
import json
import time
import socket
import threading
import credentials
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.database_saver import ContinuousDataSaver


class NetworkReader(threading.Thread):
    """ Network reader """
    def __init__(self, codenames: list):
        threading.Thread.__init__(self)
        self.name = 'NetworkReader Thread'
        self.values = {}
        self.codenames = codenames
        self.livesocket = LiveSocket('LinkamLiveFlowLogger', list(codenames))
        self.livesocket.start()
        for codename in codenames:
            self.values[codename] = None
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(1)

        self.quit = False
        self.ttl = 50

    def value(self, codename):
        """ Read temperature and  pressure """
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            self.quit = True
            return_val = None
        else:
            return_val = self.values[codename]
        return return_val

    def run(self):
        while not self.quit:
            time.sleep(0.5)
            self.ttl = 50
            for codename in self.codenames:
                time.sleep(0.1)
                cmd = '{}#json'.format(codename).encode()
                self.sock.sendto(cmd, ('127.0.0.1', 9000))
                recv = self.sock.recv(65535)
                data = json.loads(recv)
                self.values[codename] = data[1]
                self.livesocket.set_point_now(codename, data[1])


class NetworkLogger(object):
    def __init__(self):
        self.loggers = {}
        self.codenames = {
            'mfc_flow_wet_linkham': (0.5, 600),
            'mfc_flow_dry_linkham': (1.25, 600),
            'mfc_flow_wet_setpoint_linkham': (0.05, 3000),
            'mfc_flow_dry_setpoint_linkham': (0.05, 3000),
        }
        self.reader = NetworkReader(self.codenames.keys())
        self.reader.start()

        # db_names = ['mfc_flow_{}'.format(cn) for cn in self.codenames.keys()]
        db_names = self.codenames.keys()
        self.db_logger = ContinuousDataSaver(
            continuous_data_table='dateplots_linkam',
            username=credentials.user,
            password=credentials.passwd,
            measurement_codenames=db_names
        )
        self.db_logger.name = 'DB Logger Thread'
        self.db_logger.start()

        for codename, params in self.codenames.items():
            print(codename, params)
            self.loggers[codename] = ValueLogger(
                self.reader,
                comp_val=params[0],
                comp_type='lin',
                maximumtime=params[1],
                channel=codename
            )
            self.loggers[codename].name = 'Logger_thread_{}'.format(codename)
            self.loggers[codename].start()

    def main(self):
        """
        Main function
        """
        # n = 0
        while self.reader.is_alive():
            print(
                self.loggers['mfc_flow_dry_linkham'].value,
                self.loggers['mfc_flow_dry_linkham'].compare,
            )
            time.sleep(5)
            for name in self.loggers.keys():
                value = self.loggers[name].read_value()
                if self.loggers[name].read_trigged():
                    msg = '{} is logging value: {}'
                    print(msg.format(name, value))
                    self.db_logger.save_point_now(name, value)
                    self.loggers[name].clear_trigged()


if __name__ == '__main__':
    nl = NetworkLogger()
    nl.main()
