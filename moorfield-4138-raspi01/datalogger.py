import time
import threading

from PyExpLabSys.drivers.moorfield_minilab import MoorfieldMinilab
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.sockets import DataPushSocket
from PyExpLabSys.common.sockets import DateDataPullSocket

from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.database_saver import ContinuousDataSaver

import credentials

import mapping


class MoorfieldReader(threading.Thread):
    """Read values from the system"""

    def __init__(self):
        threading.Thread.__init__(self)
        self.name = 'MoorfieldReader Thread'
        self.moorfield = MoorfieldMinilab(mapping.mapping)

        self.values = {}
        for key, value in mapping.mapping.items():
            codename_key = mapping.data_table + '_' + key
            if value is not None:
                self.values[codename_key] = -1

        self.pullsocket = DateDataPullSocket(
            mapping.system_name + 'Values',
            list(self.values.keys()),
            timeouts=[3] * len(self.values),
            port=9000,
        )
        self.pullsocket.start()

        self.livesocket = LiveSocket(
            mapping.system_name + 'Live', list(self.values.keys())
        )
        self.livesocket.start()

        self.quit = False
        self.ttl = 50

    def value(self, codename):
        """Read Mercury readings"""
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            print('TTL is out! Stopping')
            self.quit = True
            return_val = None
        return_val = self.values[codename]
        return return_val

    def _update_values(self):
        codename_key = mapping.data_table + '_' + 'full_range_pressure'
        if codename_key in self.values:
            self.values[codename_key] = self.moorfield.read_full_range_gauge()

        codename_key = mapping.data_table + '_' + 'baratron_pressure'
        if codename_key in self.values:
            self.values[codename_key] = self.moorfield.read_baratron_gauge()

        codename_key = mapping.data_table + '_' + 'turbo_speed'
        if codename_key in self.values:
            self.values[codename_key] = self.moorfield.read_turbo_speed()

        for mfc in range(1, 4):
            codename_key = mapping.data_table + '_' + 'mfc_{}_flow'.format(mfc)
            if codename_key in self.values:
                flow = self.moorfield.read_mfc(mfc)
                self.values[codename_key] = flow['actual']
                codename_key = mapping.data_table + '_' + 'mfc_{}_setpoint'.format(mfc)
                if codename_key in self.values:
                    self.values[codename_key] = flow['setpoint']

        rf_params = [
            'rf_forward_power',
            'rf_reflected_power',
            'dc_bias',
            'tune_motor',
            'load_motor',
        ]
        rf_values = self.moorfield.read_rf_values()
        for param in rf_params:
            codename_key = mapping.data_table + '_' + param
            if codename_key in self.values:
                self.values[codename_key] = rf_values[param]

        for key, value in self.values.items():
            self.pullsocket.set_point_now(key, value)
            self.livesocket.set_point_now(codename_key, value)

    def run(self):
        while not self.quit:
            self.ttl = 100
            time.sleep(0.5)
            self._update_values()
            # print(self.values)


class Logger:
    def __init__(self):
        self.loggers = {}
        self.reader = MoorfieldReader()
        self.reader.start()

        codenames = {}
        for key in self.reader.values.keys():
            if 'full_range_pressure' in key:
                codenames[key] = (5, 'log')
            if 'baratron_pressure' in key:
                codenames[key] = (0.02, 'lin')
            if 'mfc' in key:
                codenames[key] = (0.25, 'lin')
            if 'turbo' in key:
                codenames[key] = (0.75, 'lin')
            if 'bias' in key:
                codenames[key] = (0.75, 'lin')
            if 'motor' in key:
                codenames[key] = (0.75, 'lin')
            if 'power' in key:
                codenames[key] = (0.5, 'lin')

        self.db_logger = ContinuousDataSaver(
            continuous_data_table='dateplots_' + mapping.data_table,
            username=credentials.user,
            password=credentials.passwd,
            measurement_codenames=codenames.keys(),
        )
        self.db_logger.name = 'DB Logger Thread'
        self.db_logger.start()

        for codename, comp_param in codenames.items():
            self.loggers[codename] = ValueLogger(
                self.reader,
                comp_val=comp_param[0],
                comp_type=comp_param[1],
                maximumtime=600,
                channel=codename,
            )
            self.loggers[codename].name = 'Logger_thread_{}'.format(codename)
            self.loggers[codename].start()

    def main(self):
        """
        Main function
        """
        time.sleep(5)
        while self.reader.is_alive():
            time.sleep(1)
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

    MR = MoorfieldReader()
    MR.start()
