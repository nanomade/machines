import time
import threading
import collections

import bme680  # From pip, not from PyExpLabSys

from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.database_saver import ContinuousDataSaver

import credentials


class BMEReader(threading.Thread):
    """ Read the BME680 environmental sensor """
    def __init__(self):
        threading.Thread.__init__(self)
        self.name = 'BMEReader Thread'
        # Sensor configured according to official recommendation from Pimoroni
        # https://learn.pimoroni.com/article/getting-started-with-bme680-breakout
        self.sensor = bme680.BME680(i2c_addr=0x77)
        self.sensor.set_humidity_oversample(bme680.OS_2X)
        self.sensor.set_pressure_oversample(bme680.OS_4X)
        self.sensor.set_temperature_oversample(bme680.OS_8X)
        self.sensor.set_filter(bme680.FILTER_SIZE_3)

        self.sensor.set_gas_status(bme680.ENABLE_GAS_MEAS)
        self.sensor.set_gas_heater_temperature(320)
        self.sensor.set_gas_heater_duration(150)
        self.sensor.select_gas_heater_profile(0)

        self.values = {
            'temperature_309_260': collections.deque(maxlen=2),
            'humidity_309_260': collections.deque(maxlen=5),
            'air_pressure_309_260': collections.deque(maxlen=3),
            'gas_resistance_309_260': collections.deque(maxlen=30)
        }
        self.quit = False
        self.ttl = 50

    def value(self, codename):
        """ Read temperature and  pressure """
        self.ttl = self.ttl - 1
        values = list(self.values[codename])
        if self.ttl < 0:
            print('TTL is out! Stopping')
            self.quit = True
            return_val = None
        elif len(values) == 0:
            return_val = None
        else:
            return_val = sum(values) / len(values)
        return return_val

    def run(self):
        while not self.quit:
            time.sleep(0.5)
            self.ttl = 50
            if not self.sensor.get_sensor_data():
                print('No data ready')
            else:
                # Todo - fill in live-socket data
                self.values['temperature_309_260'].append(
                    self.sensor.data.temperature)
                self.values['humidity_309_260'].append(self.sensor.data.humidity)
                self.values['air_pressure_309_260'].append(self.sensor.data.pressure)

                if self.sensor.data.heat_stable:
                    self.values['gas_resistance_309_260'].append(
                        self.sensor.data.gas_resistance)
                else:
                    print('Heat sensor not stable')


class Logger(object):
    def __init__(self):
        self.loggers = {}
        self.bme_reader = BMEReader()
        self.bme_reader.start()

        self.db_logger = ContinuousDataSaver(
            continuous_data_table='dateplots_environment',
            username=credentials.env_user,
            password=credentials.env_passwd,
            measurement_codenames=self.bme_reader.values.keys()
        )
        self.db_logger.name = 'DB Logger Thread'
        self.db_logger.start()

        # start environmental loggers
        for codename in self.bme_reader.values.keys():
            self.loggers[codename] = ValueLogger(
                self.bme_reader,
                comp_val=0.25,
                comp_type='lin',
                maximumtime=600,
                channel=codename
            )
            self.loggers[codename].name = 'Logger_thread_{}'.format(codename)
            self.loggers[codename].start()
        compare = {'type': 'log', 'val': 0.15}
        self.loggers['gas_resistance_309_260'].compare.update(compare)

    def main(self):
        """
        Main function
        """
        time.sleep(60)
        while self.bme_reader.is_alive():
            time.sleep(5)
            for name in self.loggers.keys():
                value = self.loggers[name].read_value()
                if self.loggers[name].read_trigged():
                    msg = '{} is logging value: {}'
                    print(msg.format(name, value))
                    self.db_logger.save_point_now(name, value)
                    self.loggers[name].clear_trigged()


if __name__ == '__main__':
    # TODO! Handle the error values!!!!!!
    # Currently they are simply ignored.
    # Handling will be highly interesting as soon as email-alarms from PyExpLabSys
    # are functional

    logger = Logger()
    logger.main()
