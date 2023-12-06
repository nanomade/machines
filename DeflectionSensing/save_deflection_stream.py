import time
from PyExpLabSys.common.database_saver import DataSetSaver, CustomColumn

from read_deflection_stream import DeflectorReader

import credentials


class DeflectionSaver:
    def __init__(self):
        self.chamber_name = 'dummy'
        self.reader = DeflectorReader()
        self.data_set_saver = DataSetSaver(
            "measurements_" + self.chamber_name,
            "xy_values_" + self.chamber_name,
            credentials.user,
            credentials.passwd,
        )
        self.data_set_saver.start()

    def start_measurement(self, comment):
        metadata = {
            'Time': CustomColumn(time.time(), "FROM_UNIXTIME(%s)"),
            'type': 57,
            'comment': comment,
        }
        metadata['label'] = 'Pressure'
        self.data_set_saver.add_measurement('p', metadata)
        metadata['label'] = 'Temperature'
        self.data_set_saver.add_measurement('t', metadata)
        metadata['label'] = 'Ref Pressure'
        self.data_set_saver.add_measurement('p_ref', metadata)
        metadata['label'] = 'Ref Temperature'
        self.data_set_saver.add_measurement('t_ref', metadata)

    def timed_recording(self, comment, record_time=300):
        self.start_measurement(comment)
        self.reader.start()

        t_start = time.time()
        now = 0
        iteration = 0
        while now < record_time:
            iteration += 1
            data = None
            while data is None:
                time.sleep(1e-3)
                data = self.reader.return_data(only_new_data=True)

            now = time.time() - t_start
            self.data_set_saver.save_point('p', (now, data['p']))
            if iteration % 10 == 0 and 't' in data:
                self.data_set_saver.save_point('t', (now, data['t']))
            if iteration % 50 == 0 and 'p_ref' in data:
                self.data_set_saver.save_point('p_ref', (now, data['p_ref']))
                self.data_set_saver.save_point('t_ref', (now, data['t_ref']))
        self.reader.stop()


if __name__ == '__main__':
    ds = DeflectionSaver()
    ds.timed_recording('test', 5)
