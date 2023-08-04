import time
import threading

from PyExpLabSys.drivers.vaisala_dmt143 import VaisalaDMT143

from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.database_saver import ContinuousDataSaver

import credentials


class VaisalaReader(threading.Thread):
    """ Read the Vaisala dew point measurement sensor """
    def __init__(self):
        threading.Thread.__init__(self)
        self.name = 'VaisalaReader Thread'
        self._connect_to_sensor()
        self.values = {
            'dew_point_linkam': -1,
            'h20_concentration_linkam': -1,
        }
        self.pullsocket = DateDataPullSocket(
            'VaisalaDewPoint',
            list(self.values.keys()),
            timeouts=[10] * len(self.values),
            port=9001
        )
        self.pullsocket.start()
        self.livesocket = LiveSocket('VaisalaLiveDewPoint', list(self.values.keys()))
        self.livesocket.start()
        self.quit = False
        self.ttl = 50

    def _connect_to_sensor(self, port='/dev/ttyUSB0'):
        print('Connecting to sensor')
        try:
            port = 'usb-Silicon_Labs_Vaisala_USB_Instrument_Cable_S3323150-if00-port0'
            self.sensor = VaisalaDMT143(port='/dev/serial/by-id/' + port)
            time.sleep(1)
        except OSError:
            print('Could not find sensor, sleep for 5 seconds')
            time.sleep(5)
        except UnicodeDecodeError:
            print('Could not find sensor, sleep for 5 seconds')
            time.sleep(5)

        try:
            # Perform a dummy-reading, sometimes this very first reading reports
            # a communication error.
            self.sensor.water_level()
        except ValueError:
            print('Error in first reading, wait 2 seconds')
            time.sleep(2)

    def value(self, codename):
        """ Read Vaisala readings """
        self.ttl = self.ttl - 1
        print('TTL is: {}'.format(self.ttl))
        if self.ttl < 0:
            print('TTL is out! Stopping')
            self.quit = True
            return_val = None
        return_val = self.values[codename]
        return return_val

    def run(self):
        while not self.quit:
            self.ttl = 100
            time.sleep(0.25)
            try:
                values = self.sensor.water_level()
            except ValueError:
                values = None
            if values is None:
                values = {'dew_point': -100, 'vol_conc': -100}
                self._connect_to_sensor()
            self.pullsocket.set_point_now('dew_point_linkam', values['dew_point'])
            self.pullsocket.set_point_now('h20_concentration_linkam', values['vol_conc'])
            self.livesocket.set_point_now('dew_point_linkam', values['dew_point'])
            self.livesocket.set_point_now('h20_concentration_linkam', values['vol_conc'])
            self.values = {
                'dew_point_linkam': values['dew_point'],
                'h20_concentration_linkam': values['vol_conc']
            }


class Logger(object):
    def __init__(self):
        self.loggers = {}
        self.vaisala_reader = VaisalaReader()
        self.vaisala_reader.start()

        codenames = {'dew_point_linkam': 0.025, 'h20_concentration_linkam': 50}
        self.db_logger = ContinuousDataSaver(
            continuous_data_table='dateplots_linkam',
            username=credentials.user,
            password=credentials.passwd,
            measurement_codenames=codenames.keys()
        )
        self.db_logger.name = 'DB Logger Thread'
        self.db_logger.start()

        for codename, comp_val in codenames.items():
            self.loggers[codename] = ValueLogger(
                self.vaisala_reader,
                comp_val=comp_val,
                comp_type='lin',
                maximumtime=600,
                channel=codename,
            )
            self.loggers[codename].name = 'Logger_thread_{}'.format(codename)
            self.loggers[codename].start()

    def main(self):
        """
        Main function
        """
        time.sleep(20)
        while self.vaisala_reader.is_alive():
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
