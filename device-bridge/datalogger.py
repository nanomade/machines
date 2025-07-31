"""UDP Value logger"""

import time
import pickle
import logging
import threading
import collections

from PyExpLabSys.common.utilities import get_logger
from PyExpLabSys.common.sockets import DataPushSocket
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.database_saver import ContinuousDataSaver

import credentials


TABLE = 'dateplots_environment'

LOGGER = get_logger(
    'Device Bridge',
    level='warning',
    file_log=True,
    file_name='device_bridge.txt',
    terminal_log=False,
    email_on_warnings=False,
    email_on_errors=True,
    file_max_bytes=104857600,
    file_backup_count=5,
)


class NetworkReader(threading.Thread):
    """Network reader"""

    def __init__(self, pushsocket, pullsocket):
        LOGGER.warning('Starting network reader')
        threading.Thread.__init__(self)
        self.name = 'NetworkReader Thread'
        self.pushsocket = pushsocket
        self.pullsocket = pullsocket
        self.values = {}

        # These are used to hold data to be send to socket
        self.latest_values = {}
        self.elements = collections.deque(maxlen=5)

        # If we want a live-socket, we make it here
        # livesocket = LiveSocket('NetworkLogger', codenames)
        # livesocket.start()
        self.quit = False
        self.ttl = 1500

    def _add_codename(self, codename):
        print('NetworkReader, adding codename {}'.format(codename))
        if codename.find('resistance') > -1:
            maxlen = 30
        else:
            maxlen = 5
        self.values[codename] = collections.deque(maxlen=maxlen)

    def value(self, channel):
        """Read temperature and  pressure"""
        self.ttl = self.ttl - 1
        if self.ttl < 200:
            print('TTL is: {}'.format(self.ttl))
        return_val = None
        if self.ttl < 0:
            print('NetworkReader TTL is 0 - quitting!')
            self.quit = True
        else:
            raw_values = self.values.get(channel, [])
            values = []
            for value in raw_values:
                if (time.time() - value[1]) < 300:
                    values.append(value[0])
            if values:
                return_val = sum(values) / len(values)
        return return_val

    def run(self):
        while not self.quit:
            time.sleep(0.5)
            self.ttl = 2500
            qsize = self.pushsocket.queue.qsize()
            self.pullsocket.set_point_now('qsize', qsize)
            if qsize > 15:
                LOGGER.warning('Queue is currently {} elements long'.format(qsize))
            while qsize > 0:
                element = self.pushsocket.queue.get()
                # print(element['location'])
                # print(element)
                # Expose element on network socket
                self.elements.append(element)
                self.pullsocket.set_point_now('latest_elements', list(self.elements))

                qsize = self.pushsocket.queue.qsize()
                location = element['location']
                for key, value in element.items():
                    if key == 'location':
                        continue
                    codename = key + '_' + location
                    if codename not in self.values:
                        self._add_codename(codename)
                    timed_value = (value, time.time())
                    self.values[codename].append(timed_value)
                    self.latest_values[codename] = timed_value
                self.pullsocket.set_point_now('latest_values', self.latest_values)
        LOGGER.error('Network reader is no longer running!!!')


class NetworkLogger(object):
    def __init__(self):
        LOGGER.warning('Starting network logger')
        # self.codenames = []
        self.loggers = {}

        self.db_logger = None
        self.pushsocket = DataPushSocket('device-bridge', action='enqueue')
        self.pushsocket.name = 'push-socket thread'
        self.pushsocket.start()

        # bridge_status: Overall status of the device bridge
        # latest_values: Dict with the latest received values
        self.pullsocket = DateDataPullSocket(
            'DeviceBridgeStatus',
            ['qsize', 'latest_values', 'latest_elements', 'dead', 'alive'],
            timeouts=[3, 5, 5, 60, 60],
            port=9000,
        )
        self.pullsocket.start()

        # Live Socket for certain especially relevant values
        self.live_list = ['humidity_309_257']
        self.livesocket = LiveSocket(
            'EnvironmentLive', self.live_list, no_internal_data_pull_socket=True
        )
        self.livesocket.start()

        self.reader = NetworkReader(self.pushsocket, self.pullsocket)
        self.reader.start()

    def add_codename(self, codename, comp_val=0.5, comp_type='lin'):
        # TODO: Allow a list of codenames, no need to
        # restart db_connection for every single item

        print('Adding codename: {}'.format(codename))
        if codename in self.loggers:
            return
        # self.codenames.append(codename)
        self.loggers[codename] = ValueLogger(
            self.reader,
            comp_val=comp_val,
            comp_type=comp_type,
            maximumtime=600,
            channel=codename,
        )
        self.loggers[codename].name = 'Logger_thread_{}'.format(codename)
        self.loggers[codename].start()

        if self.db_logger is not None:
            self.db_logger.stop()
            del self.db_logger
        self.db_logger = ContinuousDataSaver(
            continuous_data_table=TABLE,
            username=credentials.user,
            password=credentials.passwd,
            measurement_codenames=self.loggers.keys(),
        )
        self.db_logger.name = 'DB Logger Thread'
        self.db_logger.start()
        return codename

    def main(self):
        """
        Main function
        """
        # todo, should we ask the sql-server for these?
        codenames = []
        locations = {
            #'309_gas_diffusion_setup': [
            #    ('p_gas_side', 2.02, 'lin'),
            #    ('p_pump_side', 2.02, 'lin'),
            # ],
            '309_000': [
                ('house_vacuum_pressure', 2.0, 'lin'),
                ('ventilation_pressure', 4.0, 'lin'),
            ],
            # '309_245': [
            #     ('temperature', None, 'lin'),
            #     ('humidity', None, 'lin'),
            #     ('air_pressure', None, 'lin'),
            # ],
            '309_246': [
                ('temperature', None, 'lin'),
                ('humidity', None, 'lin'),
                ('air_pressure', None, 'lin'),
                ('gas_resistance', 250, 'lin'),
            ],
            '309_252': [
                ('temperature', None, 'lin'),
                ('humidity', None, 'lin'),
                ('air_pressure', None, 'lin'),
                ('gas_resistance', 250, 'lin'),
            ],
            '309_253': [
                ('temperature', None, 'lin'),
                ('humidity', None, 'lin'),
                ('air_pressure', None, 'lin'),
                ('gas_resistance', 500, 'lin'),
            ],
            '309_255': [
                ('temperature', None, 'lin'),
                ('humidity', None, 'lin'),
                ('air_pressure', None, 'lin'),
                ('gas_resistance', 500, 'lin'),
            ],
            # This needs to be merged into 309_257
            '309_257_SPINNER_FUMEHOOD': [
                ('temperature', None, 'lin'),
                ('humidity', None, 'lin'),
                ('air_pressure', None, 'lin'),
                ('gas_resistance', 400, 'lin'),
            ],
            '309_257': [
                ('temperature', None, 'lin'),
                ('humidity', None, 'lin'),
                ('air_pressure', None, 'lin'),
            ],
            # This needs to merged into 309_263
            '263_turbo_pump_temperatures': [
                ('deposition_temperature', 0.25, 'lin'),
            ],
            # This needs to merged into 309_263
            '309_moorfield_common_vacuum': [
                ('pressure', 0.1, 'log'),
                ('temperature', 1.0, 'lin'),
            ],
            '309_263': [
                ('temperature', 0.25, 'lin'),  # Unit 1
                ('humidity', None, 'lin'),  # Unit 1
                ('air_pressure', None, 'lin'),  # Unit 1
                ('new_etcher_turbo_pump_temperature', 0.25, 'lin'),  # Unit 2
                ('old_etcher_cooling_water_flow', 0.1, 'lin'),  # Unit 2
                ('new_etcher_cooling_water_flow', 0.1, 'lin'),  # Unit 2
                ('t_central_cooling_water_forward', 0.1, 'lin'),  # Unit 3
                ('t_central_cooling_water_return', 0.1, 'lin'),  # Unit 3
            ],
            '309_909': [
                ('temperature', None, 'lin'),
                ('humidity', None, 'lin'),
                ('air_pressure', None, 'lin'),
            ],
            '309_918': [
                ('temperature', None, 'lin'),
                ('humidity', None, 'lin'),
                ('air_pressure', None, 'lin'),
            ],
            '309_926': [
                ('temperature', None, 'lin'),
                ('humidity', None, 'lin'),
                ('b_field', 1e-6, 'lin'),
                ('air_pressure', None, 'lin'),
            ],
        }
        for location, elements in locations.items():
            for element in elements:
                codename = '{}_{}'.format(element[0], location)
                print(codename)
                finished_element = (codename, element[1], element[2])
                codenames.append(finished_element)
        # Todo: These two loops should be merged with
        for codename, comp_val, comp_type in codenames:
            if comp_val is None:
                comp_val = 0.5
            self.add_codename(codename, comp_val=comp_val, comp_type=comp_type)

        n = 0
        while self.reader.is_alive():
            n = (n + 1) % 100

            alive = []
            dead = []
            for codename in self.loggers.keys():
                # print(codename)
                if self.loggers[codename].is_alive():
                    alive.append(codename)
                else:
                    dead.append(codename)
            self.pullsocket.set_point_now('dead', dead)
            self.pullsocket.set_point_now('alive', alive)
            if n == 0:
                print()
                print('Alive: {}'.format(alive))
                print('Dead: {}'.format(dead))
            # todo: Attempt to re-start dead threads?

            time.sleep(2)
            latest_values = {}  # Will be supplied to socket in a short while
            for name in self.loggers.keys():
                value = self.loggers[name].read_value()

                if name in self.live_list:
                    self.livesocket.set_point_now(name, value)

                latest_values[name] = value
                if self.loggers[name].read_trigged():
                    msg = '{} is logging value: {}'
                    LOGGER.info(msg.format(name, value))
                    self.db_logger.save_point_now(name, value)
                    self.loggers[name].clear_trigged()
            self.pullsocket.set_point_now('latest_values', latest_values)

        print('Reader is not alive - quit!')


if __name__ == '__main__':
    while True:
        nl = NetworkLogger()
        # time.sleep(30)
        nl.main()
        print('Re-starting!!!!!!!')
        time.sleep(120)
