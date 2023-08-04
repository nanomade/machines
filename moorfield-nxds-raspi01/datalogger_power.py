import time
import threading

import PyExpLabSys.drivers.netio_powerbox as netio_powerbox

from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.sockets import DateDataPullSocket

from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.database_saver import ContinuousDataSaver

import credentials


class Comm(threading.Thread):
    """ Read values from the power strip """
    def __init__(self):
        threading.Thread.__init__(self)
        self.name = 'NetioReader Thread'
        self.netio_left = netio_powerbox.NetioPowerBox('10.54.5.209')
        self.netio_right = netio_powerbox.NetioPowerBox('10.54.4.120')
        self.values = {
            'power_input_voltage': -1,
            'power_input_frequency': -1,
            'power_mglove_common_vacuum': -1,
            'power_glovebox_old_etch': -1,
            'power_glovebox_new_etch': -1,
            'power_glovebox_solvent': -1,
        }
        self.pullsocket = DateDataPullSocket(
            'PowerConsumption',
            list(self.values.keys()),
            timeouts=[3] * len(self.values),
            port=9000
        )
        self.pullsocket.start()
        self.livesocket = LiveSocket(
            'PowerConsumption Live', list(self.values.keys())
        )
        self.livesocket.start()

        self.quit = False
        self.ttl = 50

    def value(self, codename):
        """ Read power readings """
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            print('TTL is out! Stopping')
            self.quit = True
            return_val = None
        return_val = self.values[codename]
        return return_val

    def _update_values(self):
        success = False
        try:
            # Should we also record phase???
            power_status_left = self.netio_left.output_status([3, 4])
            power_status_right = self.netio_right.output_status([2, 4])
            self.values['power_input_voltage'] = power_status_left[0]['Voltage']
            self.values['power_input_frequency'] = power_status_left[0]['Frequency']

            self.values['power_glovebox_old_etch'] = power_status_left[3]['Load']
            self.values['power_glovebox_solvent'] = power_status_left[4]['Load']
            self.values['power_glovebox_new_etch'] = power_status_right[2]['Load']
            self.values['power_mglove_common_vacuum'] = power_status_right[4]['Load']

            for key, value in self.values.items():
                self.pullsocket.set_point_now(key, value)
            success = True
        except Exception as e:
            print()
            print('Unable to connect to power strip - exception is: {}'.format(e))
        return success

    def run(self):
        while not self.quit:
            success = self._update_values()
            if success:
                self.ttl = 100
            time.sleep(0.75)


class Logger(object):
    def __init__(self):
        self.loggers = {}
        self.reader = Comm()
        self.reader.start()

        codenames = {
            'power_input_voltage': 0.5,
            'power_input_frequency': 0.1,
            'power_glovebox_old_etch': 5,
            'power_glovebox_new_etch': 5,
            'power_glovebox_solvent': 5,
            'power_mglove_common_vacuum': 8,
        }
        self.db_logger = ContinuousDataSaver(
            continuous_data_table='dateplots_powerconsumption',
            username=credentials.user_power,
            password=credentials.passwd_power,
            measurement_codenames=codenames.keys()
        )
        self.db_logger.name = 'DB Logger Thread'
        self.db_logger.start()

        for codename, comp_val in codenames.items():
            self.loggers[codename] = ValueLogger(
                self.reader,
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
        while self.reader.is_alive():
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
