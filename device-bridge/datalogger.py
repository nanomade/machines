""" UDP Value logger """
import time
import threading
import collections

import credentials

from PyExpLabSys.common.sockets import DataPushSocket
from PyExpLabSys.common.value_logger import ValueLogger
# from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.database_saver import ContinuousDataSaver

# TODO!!!
# Currently as long as the thread does not crash, the logging
# will continue, even if no new values are added. We need to
# invalidate data points after N minutes to prevent them from
# being re-logged.
class NetworkReader(threading.Thread):
    """ Network reader """
    def __init__(self, codenames, pushsocket):
        threading.Thread.__init__(self)
        self.pushsocket = pushsocket
        self.values = {}
        for codename in codenames:
            self.values[codename] = collections.deque(maxlen=5)
        self.codenames = codenames

        # If we want a pull- and live-socket, we make it here
        # self.pull_socket = pull_socket
        # livesocket = LiveSocket('NetworkLogger', codenames)
        # livesocket.start()

        self.quit = False
        self.ttl = 50

    def value(self, channel):
        """ Read temperature and  pressure """
        self.ttl = self.ttl - 1
        return_val = None
        if self.ttl < 0:
            self.quit = True
        else:
            raw_values = self.values.get(channel)
            values = []
            for value in raw_values:
                if (time.time() - value[1]) < 300:
                    values.append(value[0])
            if values:
                return_val = sum(values) / len(values)
        return return_val

    def run(self):
        while not self.quit:
            time.sleep(1)
            self.ttl = 50
            qsize = self.pushsocket.queue.qsize()
            while qsize > 0:
                element = self.pushsocket.queue.get()
                qsize = self.pushsocket.queue.qsize()
                name = element['location']
                for code in ['temperature', 'humidity', 'air_pressure']:
                    if code not in element:
                        continue
                    codename = code + '_' + name
                    value = (element[code], time.time())
                    self.values[codename].append(value)
                    # self.pull_socket.set_point_now(codename, value)
                    # self.live_socket.set_point_now(codename, value)


def main():
    """
    Main function
    """
    codenames = [
        'temperature_309_245', 'humidity_309_245', 'air_pressure_309_245',
        'temperature_309_257', 'humidity_309_257', 'air_pressure_309_257',
    ]

    pushsocket = DataPushSocket('device-bridge', action='enqueue')
    pushsocket.start()

    reader = NetworkReader(codenames, pushsocket)
    reader.start()

    print('Start loggers')
    loggers = {}
    for codename in codenames:
        loggers[codename] = ValueLogger(
            reader,
            comp_val=0.5,
            comp_type='lin',
            channel=codename
        )
        loggers[codename].start()

    table = 'dateplots_environment'
    print('Start db')
    db_logger = ContinuousDataSaver(
        continuous_data_table=table,
        username=credentials.user,
        password=credentials.passwd,
        measurement_codenames=codenames
    )
    print('Start logger')
    db_logger.start()

    while reader.is_alive():
        time.sleep(5)
        print('Check logger')
        for name in codenames:
            value = loggers[name].read_value()
            if loggers[name].read_trigged():
                msg = '{} is logging value: {}'
                print(msg.format(name, value))
                db_logger.save_point_now(name, value)
                loggers[name].clear_trigged()


if __name__ == '__main__':
    main()
