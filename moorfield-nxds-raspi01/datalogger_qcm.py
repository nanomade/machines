import time
import threading

from PyExpLabSys.drivers.inficon_sqc310 import InficonSQC310

from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.database_saver import ContinuousDataSaver

import credentials


class QcmReader(threading.Thread):
    """ Read values from the QCM controller """
    def __init__(self, codenames):
        threading.Thread.__init__(self)
        self.name = 'QCM Reader Thread'
        port = '/dev/serial/by-id/usb-Prolific_Technology_Inc._USB-Serial_Controller-if00-port0'
        self.inficon_qcm = InficonSQC310(port=port)
        self.values = {}
        for codename in codenames.keys():
            self.values[codename] = -1
        self.pullsocket = DateDataPullSocket(
            'MoorfieldQCM',
            list(self.values.keys()),
            timeouts=[3] * len(self.values),
            port=9002
        )
        self.pullsocket.start()

        # If we want a live-socket, we make it here
        self.livesocket = LiveSocket('QCM Live Logger', list(self.values.keys()))
        self.livesocket.start()
        
        self.quit = False
        self.ttl = 50

    def value(self, codename):
        """ Read QCM readings """
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            print('TTL is out! Stopping')
            self.quit = True
            return_val = None
        return_val = self.values[codename]
        return return_val

    def _update_values(self):
        # magnet_info = self.mercury_ips.read_magnet_details('PSU.M1')
        _, freq1, life1 = self.inficon_qcm.crystal_frequency_and_life(1)
        _, freq2, life2 = self.inficon_qcm.crystal_frequency_and_life(2)
        thickness1 = self.inficon_qcm.thickness(1)
        thickness2 = self.inficon_qcm.thickness(2)
        self.values.update(
            {
                'moorfield_deposition_qcm_1_frequency': freq1,
                'moorfield_deposition_qcm_2_frequency': freq2,
                'moorfield_deposition_qcm_1_thickness': thickness1,
                'moorfield_deposition_qcm_2_thickness': thickness1,
                'moorfield_deposition_qcm_1_crystal_life': life1,
                'moorfield_deposition_qcm_2_crystal_life': life2,
            }
        )
        for key, value in self.values.items():
            self.pullsocket.set_point_now(key, value)
            self.livesocket.set_point_now(key, value)

    def run(self):
        while not self.quit:
            self.ttl = 100
            time.sleep(0.5)
            self._update_values()


class Logger(object):
    def __init__(self):
        codenames = {
            'moorfield_deposition_qcm_1_frequency': (1.0, 600),
            'moorfield_deposition_qcm_2_frequency': (1.0, 600),
            'moorfield_deposition_qcm_1_thickness': (0.1, 1800),
            'moorfield_deposition_qcm_2_thickness': (0.1, 1800),
            'moorfield_deposition_qcm_1_crystal_life': (0.1, 1800),
            'moorfield_deposition_qcm_2_crystal_life': (0.1, 1800),
        }

        self.loggers = {}
        self.reader = QcmReader(codenames)
        self.reader.start()

        self.db_logger = ContinuousDataSaver(
            continuous_data_table='dateplots_moorfield',
            username=credentials.user_qcm,
            password=credentials.passwd_qcm,
            measurement_codenames=codenames.keys()
        )
        self.db_logger.name = 'DB Logger Thread'
        self.db_logger.start()

        for codename, conf in codenames.items():
            self.loggers[codename] = ValueLogger(
                self.reader,
                comp_val=conf[0],
                comp_type='lin',
                maximumtime=conf[1],
                channel=codename,
            )
            self.loggers[codename].name = 'Logger_thread_{}'.format(codename)
            self.loggers[codename].start()

    def main(self):
        """
        Main function
        """
        time.sleep(20)
        while self.reader.is_alive():
            time.sleep(5)
            for name in self.loggers.keys():
                value = self.loggers[name].read_value()
                if self.loggers[name].read_trigged():
                    msg = '{} is logging value: {}'
                    print(msg.format(name, value))
                    self.db_logger.save_point_now(name, value)
                    self.loggers[name].clear_trigged()


if __name__ == '__main__':
    logger = Logger()
    logger.main()
