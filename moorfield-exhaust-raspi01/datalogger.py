import time
import threading

import sys

sys.path.append('/home/pi/DFRobot_MultiGasSensor/python/raspberrypi')

from DFRobot_MultiGasSensor import *

from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.database_saver import ContinuousDataSaver

import credentials


class DeviceComm(threading.Thread):
    """Read values from a single gas detector"""

    def __init__(self, codename, i2c_bus=1, i2c_address=0x74):
        threading.Thread.__init__(self)
        self.device = DFRobot_MultiGasSensor_I2C(i2c_bus, i2c_address)

        while not self.device.change_acquire_mode(self.device.PASSIVITY):
            print('Wait for sensor')
            time.sleep(1)
        print('Connected to sensor')
        self.device.set_temp_compensation(1)  # Temperature compensation on
        time.sleep(1)

        # Part of init, the specific value returned is not important
        self.device.read_gas_concentration()
        gas_type = self.device.gastype
        self.name = 'Gas Reader Thread - {}'.format(gas_type)

        # Todo: Consider to add temperature as well
        self.concentration_value = None

        self.pullsocket = DateDataPullSocket(
            '{}Values'.format(gas_type),
            ['concentration', 'temperature'],
            timeouts=[3, 3],
            port=(9000 + i2c_bus),
        )
        self.pullsocket.start()
        # self.livesocket = LiveSocket('{}Live'.format(gas_type), ['concentration'], no_internal_data_pull_socket=True)
        # self.livesocket.start()
        self.quit = False
        self.ttl = 50

    def value(self, codename):
        """Read from device"""
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            print('TTL is out! Stopping')
            self.quit = True
            return_val = None
        return_val = self.concentration_value
        return return_val

    def _update_values(self):
        self.concentration_value = self.device.read_gas_concentration()
        # msg = '{} concentration: {:.2f}{} @ {:.2f}C'.format(
        #     self.device.gastype,
        #     self.concentration_value,
        #     self.device.gasunits,
        #     self.device.temp
        # )
        # print(msg)
        self.pullsocket.set_point_now('concentration', self.concentration_value)
        self.pullsocket.set_point_now('temperature', self.device.temp)
        # self.livesocket.set_point_now('concentration', self.concentration_value)

    def run(self):
        while not self.quit:
            self.ttl = 100
            time.sleep(1.0)
            self._update_values()


class Logger(object):
    def __init__(self):
        self.loggers = {}

        self.hf_reader = DeviceComm('gas_concentration_moorfield_exhaust_hf', 1, 0x74)
        self.hf_reader.start()

        self.h2s_reader = DeviceComm('gas_concentration_moorfield_exhaust_h2s', 2, 0x74)
        self.h2s_reader.start()

        codenames = {
            'gas_concentration_moorfield_exhaust_hf': self.hf_reader,
            'gas_concentration_moorfield_exhaust_h2s': self.h2s_reader,
        }

        self.db_logger = ContinuousDataSaver(
            continuous_data_table='dateplots_gas_concentration',
            username=credentials.user,
            password=credentials.passwd,
            measurement_codenames=codenames.keys(),
        )
        self.db_logger.name = 'DB Logger Thread'
        self.db_logger.start()

        for codename, reader in codenames.items():
            self.loggers[codename] = ValueLogger(
                reader, comp_val=0.5, comp_type='lin', maximumtime=600, channel=codename
            )
            self.loggers[codename].name = 'Logger_thread_{}'.format(codename)
            self.loggers[codename].start()

    def main(self):
        """
        Main function
        """
        time.sleep(5)
        while self.hf_reader.is_alive() and self.h2s_reader.is_alive():
            time.sleep(2)
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
