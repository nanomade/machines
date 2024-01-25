import time
import threading

from PyExpLabSys.drivers.geopal_gpu45 import GeopalGP45
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.database_saver import ContinuousDataSaver

import credentials

# Error codes:
# 1: Low Alarm
# 2: High alarm
# 3: Sensor error
# 4: OK
# 5: No sensor


class GasReader(threading.Thread):
    """ Read the gas alarm """

    def __init__(self, sensors):
        threading.Thread.__init__(self)
        self.name = 'GasalarmReader Thread'
        port = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FT5SJM7R-if00-port0'
        self.geopal = GeopalGP45(port)

        self.sensors = sensors
        self.values = {}
        for codename in sensors.keys():
            # (measured value, error code)
            self.values[codename] = 0.0
            self.values[codename + '_error'] = 5
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
            for codename, channel in self.sensors.items():
                time.sleep(0.5)
                data = self.geopal.read_sensor(channel)
                self.values[codename] = data[0]
                self.values[codename + '_error'] = data[1]


class Logger(object):
    def __init__(self):
        self.loggers = {}
        self.sensors = {
            # codename: Alarm channel
            'NH3_309_260': 1,
            'H2S_309_260': 2,
            'H2_309_260': 3,
            'H2_309_263': 4,
        }
        self.gas_reader = GasReader(self.sensors)
        self.gas_reader.start()

        db_names = ['gasalarm_{}'.format(cn) for cn in self.sensors.keys()]
        self.db_logger = ContinuousDataSaver(
            continuous_data_table='dateplots_gasalarm',
            username=credentials.gas_user,
            password=credentials.gas_passwd,
            measurement_codenames=db_names,
        )
        self.db_logger.name = 'DB Logger Thread'
        self.db_logger.start()

        # Start gas alarm loggers
        for codename in self.sensors.keys():
            self.loggers[codename] = ValueLogger(
                self.gas_reader,
                comp_val=0.1,
                comp_type='lin',
                maximumtime=600,
                channel=codename,
            )
            self.loggers[codename].name = 'Logger_thread_{}'.format(codename)
            self.loggers[codename].start()
            # self.loggers[codename + '_error'].name =
            # 'Logger_thread_{}'.format(codename)
            # self.loggers[codename].start()

    def main(self):
        """
        Main function
        """
        while self.gas_reader.is_alive():
            time.sleep(5)
            for name in self.loggers.keys():
                value = self.loggers[name].read_value()
                # error_value = self.loggers[name + '_error'].read_value()
                if self.loggers[name].read_trigged():
                    msg = '{} is logging value: {}'
                    print(msg.format(name, value))
                    db_name = 'gasalarm_{}'.format(name)
                    self.db_logger.save_point_now(db_name, value)
                    self.loggers[name].clear_trigged()


if __name__ == '__main__':
    # TODO! Handle the error values!!!!!!
    # Currently they are simply ignored.
    # Handling will be highly interesting as soon as email-alarms from PyExpLabSys
    # are functional

    gl = Logger()
    gl.main()
