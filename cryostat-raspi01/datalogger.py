import time
import threading

from PyExpLabSys.drivers.oxford_mercury import OxfordMercury
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.sockets import DataPushSocket
from PyExpLabSys.common.sockets import DateDataPullSocket

from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.database_saver import ContinuousDataSaver

import credentials


class MercuryComm(threading.Thread):
    """ Read values from the mercury controlle """
    def __init__(self):
        threading.Thread.__init__(self)
        self.name = 'MercuryReader Thread'
        self.mercury_itc = OxfordMercury(hostname='192.168.0.20')
        self.mercury_ips = OxfordMercury(hostname='192.168.0.21')
        self.values = {
            'cryostat_magnet_voltage': -1,
            'cryostat_magnet_current': -1,
            'cryostat_magnetic_field': -1,
            'cryostat_vti_pressure': -1,
            'cryostat_vti_temperature': -1,
            'cryostat_magnet_temperature': -1,
            'cryostat_sample_temperature': -1,
        }
        self.pullsocket = DateDataPullSocket(
            'Cryostatvalues',
            list(self.values.keys()),
            timeouts=[3] * len(self.values),
            port=9000
        )
        self.pullsocket.start()
        self.pushsocket = DataPushSocket('Mercury Control', action='enqueue')
        self.pushsocket.start()
        self.livesocket = LiveSocket('CryostatCoreLive',  list(self.values.keys()))
        self.livesocket.start()

        self.quit = False
        self.ttl = 50

    def _find_device(self, model):
        for i in range(0, 9):
            device = '/dev/ttyACM{}'.format(i)
            try:
                mercury = OxfordMercury(device)
                info = mercury.read_software_version()
                print(info)
            except Exception:
                info = ''
            if model in info:
                break
        return mercury

    def value(self, codename):
        """ Read Mercury readings """
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            print('TTL is out! Stopping')
            self.quit = True
            return_val = None
        return_val = self.values[codename]
        return return_val

    def _update_values(self):
        magnet_info = self.mercury_ips.read_magnet_details('PSU.M1')
        self.values['cryostat_magnet_voltage'] = magnet_info['voltage'][0]
        self.values['cryostat_magnet_current'] = magnet_info['current'][0] * 2
        self.values['cryostat_magnetic_field'] = self.mercury_ips.read_magnetic_field('GRPZ')[0]

        self.values['cryostat_vti_pressure'] = self.mercury_itc.read_pressure('DB8.P1')[0]
        self.values['cryostat_vti_temperature'] = self.mercury_itc.read_temperature('DB6.T1')[0]
        self.values['cryostat_magnet_temperature'] = self.mercury_itc.read_temperature('DB7.T1')[0]
        self.values['cryostat_sample_temperature'] = self.mercury_itc.read_temperature('MB1.T1')[0]
        for key, value in self.values.items():
            self.pullsocket.set_point_now(key, value)
            self.livesocket.set_point_now(key, value)

    def _handle_element(self, element):
        print(element)
        cmd = element['cmd']
        if cmd == 'sample_temperature_setpoint':
            setpoint = element.get('setpoint')
            self.mercury_itc.temperature_setpoint('MB1.T1', setpoint)

        if cmd == 'vti_temperature_setpoint':
            setpoint = element.get('setpoint')
            self.mercury_itc.temperature_setpoint('DB6.T1', setpoint)

        if cmd == 'b_field_setpoint':
            setpoint = element.get('setpoint')
            print(self.mercury_ips.b_field_setpoint('GRPZ', setpoint))

    def run(self):
        while not self.quit:
            self.ttl = 100
            time.sleep(0.5)
            qsize = self.pushsocket.queue.qsize()
            while qsize > 0:
                element = self.pushsocket.queue.get()
                self._handle_element(element)
                qsize = self.pushsocket.queue.qsize()
            self._update_values()


class Logger(object):
    def __init__(self):
        self.loggers = {}
        self.reader = MercuryComm()
        self.reader.start()

        # codenames = {'cryostat_vti_pressure': 0.1, 'cryostat_vti_temperature': 1}
        codenames = {
            'cryostat_vti_pressure': 0.1, 'cryostat_vti_temperature': 0.5,
            'cryostat_magnet_temperature': 0.2, 'cryostat_sample_temperature': 0.2,
            'cryostat_magnet_voltage': 0.05, 'cryostat_magnet_current': 0.1,
            'cryostat_magnetic_field': 0.005
        }
        self.db_logger = ContinuousDataSaver(
            continuous_data_table='dateplots_cryostat',
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
