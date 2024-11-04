"""
Logger of Vigor glove boxes using an ADC and a breakout of the
internal sensor signals.
"""
import time
import threading

import ADS1115

from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.sockets import DateDataPullSocket

from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.database_saver import ContinuousDataSaver

import credentials


PARAMETERS = ['ar_left', 'ar_right', 'n2_left', 'n2_right']

class Reader(threading.Thread):
    """ Read values from the mercury controller """
    def __init__(self, adc_mapping: dict) -> None:
        threading.Thread.__init__(self)
        self.name = 'Reader Thread'

        self.adc_mapping = adc_mapping
        self.adcs = {}
        self.values = {}
        for addr, adc_map in adc_mapping.items():
            self.adcs[addr] = ADS1115.ADS1115(address=addr)
            for name in PARAMETERS:
                codename = adc_map['prefix'] + '_' + name
                self.values[codename] = -1

        self.pullsocket = DateDataPullSocket(
            'GloveboxValues',
            list(self.values.keys()),
            timeouts=[10] * len(self.values),
            port=9000
        )
        self.pullsocket.start()
        self.livesocket = LiveSocket('GasLevelsLive',  list(self.values.keys()))
        self.livesocket.start()
        self.quit = False
        self.ttl = 50

    def value(self, codename):
        """ Read a stored value if TTL is valid """
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            print('TTL is out! Stopping')
            self.quit = True
            return_val = None
        return_val = self.values[codename]
        return return_val

    def _update_values(self):
        """
        Iterate over alle ADCs and channels and measure values
        """
        for addr, adc_mapping in self.adc_mapping.items():
            adc = self.adcs[addr]
            prefix = adc_mapping['prefix']
            for parameter in PARAMETERS:
                codename = prefix + '_' + parameter
                channel = adc_mapping[parameter][0]
                offset =  adc_mapping[parameter][1]
                scale =  adc_mapping[parameter][2]

                voltage = 0
                for _ in range(0, 8):  # Integrate for 1s
                    voltage += adc.readADCSingleEnded(channel=channel, sps=8) / 1000.0
                voltage = voltage / 8.0

                scaled_result = scale * voltage + offset
                self.values[codename] = scaled_result

                self.pullsocket.set_point_now(codename, scaled_result)
                self.livesocket.set_point_now(codename, scaled_result)

    def run(self):
        while not self.quit:
            self.ttl = 100
            # time.sleep(0.5)
            self._update_values()


class Logger():
    def __init__(self):
        self.loggers = {}

        codenames = {
            'gas_level_ar_left': 0.25,
            'gas_level_ar_right': 0.25,
            'gas_level_n2_left': 0.25,
            'gas_level_n2_right': 0.25,
        }
        # Adresses and mapping of each adc
        # The keys are i2c adresses, the values are the the three parameters and the prefix
        # The parameteres has values that are lists of channel number, offset and scale

        fullscale = 250.0
        r_measure = 150.1
        scale = 1000 * fullscale / (16 * r_measure)
        offset = -4 * fullscale / 16
        
        adc_mapping = {
            0x49: {
                'ar_left': [3, offset, scale],
                'ar_right': [2, offset, scale],
                'n2_left': [1, offset, scale],
                'n2_right': [0, offset, scale],
                'prefix': 'gas_level'
            },
            # 0x48: {
            # 'ar_left': [3, offset, scale],
            #     'ar_right': [2, offset, scale],
            #     'n2_left': [1, offset, scale],
            #    'n2_right': [0, offset, scale],
            #    'prefix': 'gas_level'
            # }
        }
        self.reader = Reader(adc_mapping=adc_mapping)
        self.reader.start()

        self.db_logger = ContinuousDataSaver(
            continuous_data_table='dateplots_gas_yard',
            username=credentials.user,
            password=credentials.passwd,
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
        time.sleep(5)
        while self.reader.is_alive():
            time.sleep(5)
            for name, data_logger in self.loggers.items():
                value = data_logger.read_value()
                if data_logger.read_trigged():
                    msg = '{} is logging value: {}'
                    print(msg.format(name, value))
                    self.db_logger.save_point_now(name, value)
                    data_logger.clear_trigged()


if __name__ == '__main__':
    logger = Logger()
    logger.main()
