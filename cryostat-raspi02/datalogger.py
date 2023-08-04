import time
import threading

from PyExpLabSys.drivers.sumitomo_f70 import SumitomoF70

from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.database_saver import ContinuousDataSaver

import credentials


PORT = '/dev/serial/by-id/usb-Prolific_Technology_Inc._USB-Serial_Controller-if00-port0'


class DeviceComm(threading.Thread):
    """ Read values from the compressor """
    def __init__(self, codenames):
        threading.Thread.__init__(self)
        self.name = 'F70 reader Thread'
        self.device = SumitomoF70(PORT)
        self.values = {}
        for codename in codenames:
            self.values[codename] = -1

        self.pullsocket = DateDataPullSocket(
            'SumitomoF70Values',
            list(self.values.keys()),
            timeouts=[3] * len(self.values),
            port=9000
        )
        self.pullsocket.start()
        self.livesocket = LiveSocket(
            'CryostatCompressorLive',  list(self.values.keys())
        )
        self.livesocket.start()
        self.quit = False
        self.ttl = 50

    def value(self, codename):
        """ Read from device """
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            print('TTL is out! Stopping')
            self.quit = True
            return_val = None
        return_val = self.values[codename]
        return return_val

    def _update_values(self):
        temperatures = self.device.read_temperature()
        pressure = self.device.read_pressure()
        if temperatures is None or pressure is None:
            print('Too many errors')
            del(self.device)
            time.sleep(2)
            self.device = SumitomoF70(PORT)
            return

        for key, value in temperatures.items():
            self.values['cryo_compressor_' + key] = value
        self.values['cryo_compressor_pressure'] = pressure

        for key, value in self.values.items():
            self.pullsocket.set_point_now(key, value)
            self.livesocket.set_point_now(key, value)

    def run(self):
        while not self.quit:
            self.ttl = 100
            time.sleep(1.0)
            self._update_values()


class Logger(object):
    def __init__(self):
        self.loggers = {}

        codenames = {
            'cryo_compressor_discharge_temp': 0.5,
            'cryo_compressor_water_outlet_temp': 0.5,
            'cryo_compressor_water_inlet_temp': 0.5,
            'cryo_compressor_pressure': 0.5
        }
        
        self.reader = DeviceComm(codenames.keys())
        self.reader.start()

        self.db_logger = ContinuousDataSaver(
            continuous_data_table='dateplots_cryo_compressor',
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
