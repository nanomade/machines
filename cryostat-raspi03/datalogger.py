import time
import threading

from daqhats import mcc134, TcTypes, hat_list

from PyExpLabSys.auxiliary.rtd_calculator import RtdCalculator

from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.database_saver import ContinuousDataSaver

# We have to acknowledge that this is better than the PyExpLabsys driver :)
import ADS1x15

import credentials


class RtdComm(threading.Thread):
    """Read values from the RTDs"""

    def __init__(self, codenames):
        threading.Thread.__init__(self)
        self.name = 'RTD reader'

        # Standard PT100, 100ohm at 0C
        self.rtd_calc = RtdCalculator(0, 100)

        self.ads = ADS1x15.ADS1115(1)
        self.ads.setGain(16)  # Max voltage 0.256V
        self.ads.setDataRate(0)  # 8sps, slowest rate
        self.ads.setMode(1)  # Single-shot conversion

        self.v_source = 3.3  # V
        self.r_shunt = 2200  # ohm
        self.channels = (
            self.ads.readADC_Differential_0_1,
            self.ads.readADC_Differential_2_3,
        )

        self.values = {}
        for codename in codenames:
            self.values[codename] = -1

        # This needs to be shared!
        # self.livesocket = LiveSocket(
        #     'CryostatRtdTemperaturesLive',  list(self.values.keys())
        # )
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
        return_val = self.values[codename]
        return return_val

    def _update_values(self):
        i = 0
        for codename in self.values.keys():
            channel = self.channels[i]
            # if type is function then:
            raw_count = channel()
            # if type is int then:
            # raw_diff = ADS.readADC(channel)

            v_rtd = self.ads.toVoltage(raw_count)
            # I feel that we are igonring wire voltage drop, is this
            # even better than 2w measurement?
            v_rshunt = self.v_source - v_rtd
            # print('Vrtd: {}. Vr: {}'.format(v_rtd, v_rshunt))

            r_rtd = self.r_shunt * v_rtd / v_rshunt
            temperature = self.rtd_calc.find_temperature(r_rtd)

            self.values[codename] = temperature
            i = i + 1

        for key, value in self.values.items():
            # self.pullsocket.set_point_now(key, value)
            # self.livesocket.set_point_now(key, value)
            pass

    def run(self):
        while not self.quit:
            self.ttl = 100
            time.sleep(1.0)
            self._update_values()


class TcComm(threading.Thread):
    """Read values from the thermo couples"""

    def __init__(self, codenames):
        threading.Thread.__init__(self)
        self.name = 'TC reader'

        # Channels can any of 0, 1, 2, 3, but please use the channels configured
        # with codenames
        self.channels = (0, 1, 2, 3)

        # Only a single unit is mounted - really the address is just always zero...
        address = hat_list()[0].address
        self.hat = mcc134(address)
        for channel in self.channels:
            self.hat.tc_type_write(channel, TcTypes.TYPE_K)

        self.values = {}
        for codename in codenames:
            self.values[codename] = -1

        # self.pullsocket = DateDataPullSocket(
        #     'SumitomoF70Values',
        #     list(self.values.keys()),
        #     timeouts=[3] * len(self.values),
        #     port=9000
        # )
        # self.pullsocket.start()
        self.livesocket = LiveSocket(
            'CryostatTcTemperaturesLive', list(self.values.keys())
        )
        self.livesocket.start()
        self.quit = False
        self.ttl = 50

    def value(self, codename):
        """Read from device"""
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            print('TTL is out! Stopping')
            self.quit = True
            return_val = None
        return_val = self.values[codename]
        return return_val

    def _update_values(self):
        i = 0
        for codename in self.values.keys():
            channel = self.channels[i]
            temperature = self.hat.t_in_read(channel)
            self.values[codename] = temperature
            i = i + 1

        for key, value in self.values.items():
            # self.pullsocket.set_point_now(key, value)
            self.livesocket.set_point_now(key, value)

    def run(self):
        while not self.quit:
            self.ttl = 100
            time.sleep(1.0)
            self._update_values()


class Logger(object):
    def __init__(self):
        self.loggers = {}

        rtd_codenames = {
            'cryostat_ovc_rtd_temp': 0.5,
            'cryostat_circ_pump_rtd_temp': 0.5,
        }

        tc_codenames = {
            'cryostat_cooling_water_return_tc_temp': 0.5,
            'cryostat_he_return_tc_temp': 0.5,
            'cryostat_sample_space_tc_temp': 0.5,
            'cryostat_magnet_feedthrough_tc_temp': 0.5,
        }

        self.tc_reader = TcComm(tc_codenames.keys())
        self.tc_reader.start()

        self.rtd_reader = RtdComm(rtd_codenames.keys())
        self.rtd_reader.start()

        self.db_logger = ContinuousDataSaver(
            continuous_data_table='dateplots_cryostat',
            username=credentials.user,
            password=credentials.passwd,
            measurement_codenames=list(tc_codenames.keys())
            + list(rtd_codenames.keys()),
        )
        self.db_logger.name = 'DB Logger Thread'
        self.db_logger.start()

        for codename, comp_val in tc_codenames.items():
            self._start_logger(codename, self.tc_reader, comp_val)
        for codename, comp_val in rtd_codenames.items():
            self._start_logger(codename, self.rtd_reader, comp_val)

    def _start_logger(self, codename, reader, comp_val):
        self.loggers[codename] = ValueLogger(
            reader,
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
        while self.tc_reader.is_alive():  # and rtd_reader
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
