import time
import numpy as np

from PyExpLabSys.drivers.srs_sr830 import SR830
from PyExpLabSys.common.database_saver import DataSetSaver, CustomColumn

import credentials


class NoiseSpectrumRecorder:
    def __init__(self, port='/dev/ttyUSB0'):
        self.lock_in = SR830('serial', device='/dev/ttyUSB0')
        self.chamber_name = 'dummy'
        # self.chamber_name = 'noise_spectrum'
        self.data_set_saver = DataSetSaver(
            "measurements_" + self.chamber_name,
            "xy_values_" + self.chamber_name,
            credentials.user,
            credentials.passwd,
        )
        self.data_set_saver.start()
        self.current_data = {
            'x': -1,
            'y': -1,
            'freq': -1,
        }
        self.measurement_running = False
        self.abort = False

    def _perform_xy_measurement(self, acquisition_time, frequency=None):
        if frequency is not None:
            self.lock_in.use_internal_freq_reference(frequency)
            time.sleep(5)
        t = time.time()
        delta_t = 0
        while delta_t < acquisition_time:
            if self.abort:
                self.abort = False
                break
            delta_t = time.time() - t
            data = self.lock_in.read_x_and_y_noise()
            self.data_set_saver.save_point('x_noise', (delta_t, data[0]))
            self.data_set_saver.save_point('y_noise', (delta_t, data[1]))
            self.data_set_saver.save_point('x_value', (delta_t, data[2]))
            self.data_set_saver.save_point('y_value', (delta_t, data[3]))
            self.current_data.update({'x': data[2], 'y': data[3]})

    def _perform_sweeped_xy_measurement(self, time_pr_step, frequencies):
        self.lock_in.use_internal_freq_reference(frequencies[0])
        time.sleep(5)
        t_start = time.time()

        for freq in frequencies:
            if self.abort:
                self.abort = False
                break

            t = time.time()
            delta_t = 0
            self.lock_in.use_internal_freq_reference(freq)
            while delta_t < time_pr_step:
                if self.abort:
                    # self.abort is reset to False in the outer loop
                    break
                delta_t = time.time() - t
                total_t = time.time() - t_start
                data = self.lock_in.read_x_and_y_noise()
                self.data_set_saver.save_point('freq', (total_t, freq))
                self.data_set_saver.save_point('x_noise', (total_t, data[0]))
                self.data_set_saver.save_point('y_noise', (total_t, data[1]))
                self.data_set_saver.save_point('x_value', (total_t, data[2]))
                self.data_set_saver.save_point('y_value', (total_t, data[3]))
                self.current_data = {'x': data[2], 'y': data[3], 'freq': freq}

    def _perform_spectrum_measurement(self, frequencies):
        data = {}
        for freq in frequencies:
            if self.abort:
                self.abort = False
                break
            data = self.lock_in.estimate_noise_at_frequency(freq)
            if data is None:
                print('Could not record data at {}Hz'.format(freq))
                continue
            self.data_set_saver.save_point('x_noise', (freq, data[0]))
            self.data_set_saver.save_point('y_noise', (freq, data[1]))
            self.data_set_saver.save_point('x_value', (freq, data[2]))
            self.data_set_saver.save_point('y_value', (freq, data[3]))
            self.current_data = {'x': data[2], 'y': data[3], 'freq': freq}

    def _caluculate_frequency_steps(self, freq_high, freq_low, steps, log_scale=True):
        if log_scale:
            high = np.log10(freq_high)
            low = np.log10(freq_low)
        else:
            high = freq_high
            low = freq_low
        step_size = (high - low) / steps
        step_list = np.arange(high, low, -1 * step_size)
        step_list = np.append(step_list, low)

        if log_scale:
            step_list = 10**step_list
        return step_list

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

    def _prepare_data_recording(self, metadata, frequency_as_y=False):
        metadata.update({'label': 'X Noise'})
        self.data_set_saver.add_measurement('x_noise', metadata)
        metadata.update({'label': 'Y Noise'})
        self.data_set_saver.add_measurement('y_noise', metadata)
        metadata.update({'label': 'X Value'})
        self.data_set_saver.add_measurement('x_value', metadata)
        metadata.update({'label': 'Y Value'})
        self.data_set_saver.add_measurement('y_value', metadata)
        if frequency_as_y:
            metadata.update({'label': 'Frequency'})
            self.data_set_saver.add_measurement('freq', metadata)
        return True

    def read_current_data(self):
        # If measurement is running, the data-record process
        # is reponsible for keeping self.current_data up to data
        if not self.measurement_running:
            x, y, f = self.lock_in.read_x_and_y()
            self.current_data = {'x': x, 'y': y, 'freq': f}
        return self.current_data

    def abort_measurement(self):
        aborted = False
        if self.measurement_running:
            self.abort = True
            aborted = True
        return aborted

    # Todo: measurement_running could be handled as a context manager
    def record_spectrum(self, comment, high, low, steps, log_scale=True, **kwargs):
        self.measurement_running = True
        metadata = self._read_metadata(210, comment)
        del metadata['frequency']  # This is scanned
        self._prepare_data_recording(metadata)
        frequencies = self._caluculate_frequency_steps(high, low, steps, log_scale)
        self._perform_spectrum_measurement(frequencies)
        self.measurement_running = False
        print('record spectrum done')

    def record_xy_measurement(
        self, comment, acquisition_time, frequency=None, **kwargs
    ):
        self.measurement_running = True
        if frequency is not None:
            self.lock_in.use_internal_freq_reference(frequency)
        metadata = self._read_metadata(211, comment)
        del metadata['voltage']  # This is recorded as y-value
        self._prepare_data_recording(metadata)
        self._perform_xy_measurement(acquisition_time)
        self.measurement_running = False
        print('record_xy_measurement done')

    def record_sweeped_xy_measurement(
        self, comment, time_pr_step, high, low, steps, log_scale, **kwargs
    ):
        self.measurement_running = True
        metadata = self._read_metadata(212, comment)
        del metadata['voltage']  # This is recorded as y-value
        del metadata['frequency']  # This is recorded as y-value
        self._prepare_data_recording(metadata, frequency_as_y=True)
        frequencies = self._caluculate_frequency_steps(high, low, steps, log_scale)
        self._perform_sweeped_xy_measurement(time_pr_step, frequencies)
        self.measurement_running = False
        print('record sweeped xy measurements done')


if __name__ == '__main__':
    nsr = NoiseSpectrumRecorder()

    frequency_steps = {'high': 1e5, 'low': 25, 'steps': 7, 'log_scale': False}

    # nsr.record_spectrum(comment='100Mohm resistor', **frequency_steps)
    # nsr.record_xy_measurement(comment='100Mohm resistor', acquisition_time=100, frequency=765.2)
    nsr.record_sweeped_xy_measurement(
        comment='100Mohm resistor', time_pr_step=10, **frequency_steps
    )
