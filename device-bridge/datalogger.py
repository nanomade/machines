""" UDP Value logger """
import time
import pickle
import threading
import collections

import credentials

from PyExpLabSys.common.sockets import DataPushSocket
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.database_saver import ContinuousDataSaver


TABLE = 'dateplots_environment'


class NetworkReader(threading.Thread):
    """ Network reader """
    def __init__(self, pushsocket, pullsocket):
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
        self.ttl = 50

    def _add_codename(self, codename):
        print('NetworkReader, adding codename {}'.format(codename))
        if codename.find('resistance') > -1:
            maxlen = 20
        else:
            maxlen = 5
        self.values[codename] = collections.deque(maxlen=maxlen)

    def value(self, channel):
        """ Read temperature and  pressure """
        self.ttl = self.ttl - 1
        return_val = None
        if self.ttl < 0:
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
            self.ttl = 50
            qsize = self.pushsocket.queue.qsize()
            self.pullsocket.set_point_now('qsize', qsize)

            if qsize > 5:
                print('Queue is currently {} elements long'.format(qsize))
            while qsize > 0:
                element = self.pushsocket.queue.get()

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


class NetworkLogger(object):
    def __init__(self):
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
            port=9000
        )
        self.pullsocket.start()

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
            channel=codename
        )
        self.loggers[codename].name = 'Logger_thread_{}'.format(codename)
        self.loggers[codename].start()

        if self.db_logger is not None:
            self.db_logger.stop()
            del(self.db_logger)
        self.db_logger = ContinuousDataSaver(
            continuous_data_table=TABLE,
            username=credentials.user,
            password=credentials.passwd,
            measurement_codenames=self.loggers.keys()
        )
        self.db_logger.name = 'DB Logger Thread'
        self.db_logger.start()
        return codename

    def main(self):
        """
        Main function
        """
        # todo, should we ask the sql-server for these?
        codenames = [
            ('temperature_309_245', None, 'lin'),
            ('humidity_309_245', None, 'lin'),
            ('air_pressure_309_245', None, 'lin'),
            ('temperature_309_257', None, 'lin'),
            ('humidity_309_257', None, 'lin'),
            ('air_pressure_309_257', None, 'lin'),
            ('house_vacuum_pressure_309_000', 2.0, 'lin'),
            ('ventilation_pressure_309_000', 2.0, 'lin'),
            ('temperature_309_263', 0.25, 'lin'),
            ('humidity_309_263', None, 'lin'),
            ('air_pressure_309_263', None, 'lin'),
            ('temperature_309_909', None, 'lin'),
            ('humidity_309_909', None, 'lin'),
            ('air_pressure_309_909', None, 'lin'),
            ('temperature_309_926', None, 'lin'),
            ('humidity_309_926', None, 'lin'),
            ('b_field_309_926', 1e-6, 'lin'),
            ('air_pressure_309_926', None, 'lin'),
            ('temperature_309_252', None, 'lin'),
            ('humidity_309_252', None, 'lin'),
            ('air_pressure_309_252', None, 'lin'),
            ('gas_resistance_309_252', 250, 'lin'),
            ('temperature_309_253', None, 'lin'),
            ('humidity_309_253', None, 'lin'),
            ('air_pressure_309_253', None, 'lin'),
            ('gas_resistance_309_253', 400, 'lin'),
            ('temperature_309_255', None, 'lin'),
            ('humidity_309_255', None, 'lin'),
            ('air_pressure_309_255', None, 'lin'),
            ('gas_resistance_309_255', 400, 'lin'),
            ('temperature_309_918', None, 'lin'),
            ('humidity_309_918', None, 'lin'),
            ('air_pressure_309_918', None, 'lin'),
            ('deposition_temperature_263_turbo_pump_temperatures', 0.25, 'lin'),
            ('old_etcher_cooling_water_flow_309_263', 0.1, 'lin'),
            ('p_gas_side_309_gas_diffusion_setup', 2.02, 'lin'),
            ('p_pump_side_309_gas_diffusion_setup', 2.02, 'lin'),
            ('pressure_309_moorfield_common_vacuum', 0.1, 'log'),
            ('temperature_309_moorfield_common_vacuum', 1.0, 'lin'),
            ('t_central_cooling_water_forward_309_263', 0.1, 'lin'),
            ('t_central_cooling_water_return_309_263', 0.1, 'lin'),
        ]

        for codename, comp_val, comp_type in codenames:
            if comp_val is None:
                comp_val = 0.5
            self.add_codename(codename, comp_val=comp_val, comp_type=comp_type)

        n = 0
        while self.reader.is_alive():
            n = (n + 1) % 50

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
                print('Alive: {}'.format(alive))
                print('Dead: {}'.format(dead))
            # todo: Attempt to re-start dead threads?

            time.sleep(2)
            latest_values = {} # Will be supplied to socket in a short while
            for name in self.loggers.keys():
                value = self.loggers[name].read_value()
                latest_values[name] = value
                if self.loggers[name].read_trigged():
                    msg = '{} is logging value: {}'
                    print(msg.format(name, value))
                    self.db_logger.save_point_now(name, value)
                    self.loggers[name].clear_trigged()
            self.pullsocket.set_point_now('latest_values', latest_values)

if __name__ == '__main__':
    nl = NetworkLogger()
    nl.main()
