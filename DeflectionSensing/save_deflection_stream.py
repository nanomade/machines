import time
import threading

from PyExpLabSys.common.database_saver import DataSetSaver, CustomColumn

from read_deflection_stream import DeflectionReader

import credentials


class DeflectionSaver(threading.Thread):
    """
    Save a deflection measurement.
    Can be run 'infinitely' by simply run()'ing, or a times
    measurement can be performed.
    """

    def __init__(self):
        super().__init__()

        self.chamber_name = 'dummy'
        self.reader = DeflectionReader()
        self.data_set_saver = DataSetSaver(
            "measurements_" + self.chamber_name,
            "xy_values_" + self.chamber_name,
            credentials.user,
            credentials.passwd,
        )
        self.data_set_saver.start()
        self.data = None
        self.comment = None

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

    def stop_recording(self):
        self.comment = None

    def run(self):
        if self.comment is None:
            return

        self.start_measurement(self.comment)
        self.reader.start()

        iteration = 0
        t_start = time.time()
        while self.comment is not None:
            now = time.time() - t_start
            iteration += 1
            data = None
            while data is None:
                time.sleep(1e-3)
                data = self.reader.return_data(only_new_data=True)
            self.data = data
            self.data_set_saver.save_point('p', (now, data['p']))
            if iteration % 10 == 0 and 't' in data:
                self.data_set_saver.save_point('t', (now, data['t']))
            if iteration % 50 == 0 and 'p_ref' in data:
                self.data_set_saver.save_point('p_ref', (now, data['p_ref']))
                self.data_set_saver.save_point('t_ref', (now, data['t_ref']))
        self.reader.stop()

    def infinite_recording(self, comment):
        self.comment = comment
        self.start()

    def timed_recording(self, comment, record_time=300):
        t_start = time.time()
        self.comment = comment
        self.start()
        now = 0
        while True:
            time.sleep(0.25)
            now = time.time() - t_start
            if now > record_time:
                break
        self.stop_recording()
        self.reader.stop()


if __name__ == '__main__':
    ds = DeflectionSaver()

    print('First recording')
    ds.timed_recording('First recording', 15)
    time.sleep(5)

    print('Second recording')
    ds = DeflectionSaver()
    ds.timed_recording('Second recording', 15)
    time.sleep(5)

    print('Third recording')
    ds = DeflectionSaver()
    ds.timed_recording('Third recording', 15)
    time.sleep(5)
