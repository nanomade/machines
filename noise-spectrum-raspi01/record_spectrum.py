import time

from PyExpLabSys.drivers.srs_sr830 import SR830
from PyExpLabSys.common.database_saver import DataSetSaver, CustomColumn

import credentials


class NoiseSpectrumRecorder():
    def __init__(self, port='/dev/ttyUSB0'):
        self.lock_in = SR830('serial', device='/dev/ttyUSB0')
        self.chamber_name = 'dummy'
        # self.chamber_name = 'noise_spectrum'
        self.data_set_saver = DataSetSaver("measurements_" + self.chamber_name,
                                           "xy_values_" + self.chamber_name,
                                           credentials.user, credentials.passwd)
        self.data_set_saver.start()

    def _perform_xy_measurement(self, acquisition_time):
        t = time.time()
        delta_t = 0
        while delta_t < acquisition_time:
            delta_t = time.time() - t
            data = self.lock_in.read_x_and_y_noise()
            self.data_set_saver.save_point('x_noise', (delta_t, data[0]))
            self.data_set_saver.save_point('y_noise', (delta_t, data[1]))
            self.data_set_saver.save_point('x_value', (delta_t, data[2]))
            self.data_set_saver.save_point('y_value', (delta_t, data[3]))

    def _perform_spectrum_measurement(self):
        data = {}
        for i in range(500, 10, -1):
            exponent = i / 100.0
            freq = 10**exponent
            data = self.lock_in.estimate_noise_at_frequency(freq)
            if data is None:
                print('Could not record data at {}Hz'.format(freq))
                continue
            self.data_set_saver.save_point('x_noise', (freq, data[0]))
            self.data_set_saver.save_point('y_noise', (freq, data[1]))
            self.data_set_saver.save_point('x_value', (freq, data[2]))
            self.data_set_saver.save_point('y_value', (freq, data[3]))

    def _read_metadata(self, data_type, comment):
        # Theta and frequency is currently not logged
        r, _, freq = self.lock_in.read_r_and_theta()
        timeconstant = self.lock_in.time_constant()
        input_config = self.lock_in.input_configuration()
        sensitivity = self.lock_in.sensitivity()
        reserve = self.lock_in.reserve_configuration()
        slope = self.lock_in.filter_slope()
        slope_text = '{}dB/oct'.format(slope)

        metadata = {
            'comment': comment,
            'type': data_type,
            'time': CustomColumn(time.time(), "FROM_UNIXTIME(%s)"),
            'voltage': r,
            'frequency': freq,
            'timeconstant': timeconstant,
            'sensitivity': sensitivity,
            'reserve': reserve,
            'slope': slope_text,
            'coupling': input_config['summary'],
        }
        return metadata

    def _prepare_data_recording(self, metadata):
        metadata.update({'label': 'X Noise'})
        self.data_set_saver.add_measurement('x_noise', metadata)
        metadata.update({'label': 'Y Noise'})
        self.data_set_saver.add_measurement('y_noise', metadata)
        metadata.update({'label': 'X Value'})
        self.data_set_saver.add_measurement('x_value', metadata)
        metadata.update({'label': 'Y Value'})
        self.data_set_saver.add_measurement('y_value', metadata)
        return True

    def record_spectrum(self, comment):
        metadata = self._read_metadata(210, comment)
        del(metadata['frequency'])  # This is scanned
        self._prepare_data_recording(metadata)
        self._perform_spectrum_measurement()

    def record_xy_measurement(self, comment, acquisition_time):
        metadata = self._read_metadata(211, comment)
        del(metadata['voltage'])  # This is recorded as y-value
        self._prepare_data_recording(metadata)
        self._perform_xy_measurement(acquisition_time)


if __name__ == '__main__':
    nsr = NoiseSpectrumRecorder()
    # nsr.record_spectrum(comment='100Mohm resistor')

    nsr.record_xy_measurement(comment='100Mohm resistor', acquisition_time=100)
