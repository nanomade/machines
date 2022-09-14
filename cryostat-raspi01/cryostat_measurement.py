import time
# import logging
import threading

import Gpib  # linux-gpib, user space wrapper to kernel driver

# from PyExpLabSys.drivers.scpi import SCPI
from PyExpLabSys.drivers.srs_sr830 import SR830
from PyExpLabSys.drivers.keithley_2000 import Keithley2000
from PyExpLabSys.drivers.keithley_2182 import Keithley2182
from PyExpLabSys.drivers.keithley_2400 import Keithley2400
from PyExpLabSys.drivers.keithley_6220 import Keithley6220
# Todo: Check why CustomColumn is needed???
from PyExpLabSys.common.database_saver import DataSetSaver, CustomColumn

import credentials


CURRENT_MEASUREMENT_PROTOTYPE = {
    'type': None,  # DC-sweep, AC-sweep
    'error': None,
    'start_time': 0,
    'current_time': 0,
    'current': [],
    'v_total': [],
    'v_sample': [],
    'theta': [],
    'v_backgate': [],  # Back gate voltage
    'i_backgate': []  # Bakc gate leak-current
}


class CrystatMeasurement(object):
    def __init__(self):
        self.current_measurement = CURRENT_MEASUREMENT_PROTOTYPE.copy()
        self.lock_in = SR830(interface='gpib', gpib_address=8)
        self.nanov1 = Keithley2182(interface='gpib', gpib_address=7)
        self.current_source = Keithley6220(interface='gpib', gpib_address=12)
        self.dmm = Keithley2000(interface='gpib', gpib_address=16)
        self.back_gate = Keithley2400(interface='gpib', gpib_address=22)

        self.chamber_name = "dummy"

        self.lock_in_frequency = None
        self.set_lock_in_frequency(1010)
        self.data_set_saver = DataSetSaver("measurements_" + self.chamber_name,
                                           "xy_values_" + self.chamber_name,
                                           credentials.user, credentials.passwd)
        self.data_set_saver.start()

    def _identify_all_instruments(self):
        found_all = True
        try:
            nanov1_id = self.nanov1.read_software_version()
        except Gpib.gpib.GpibError:
            nanov1_id = ''
        if nanov1_id.find('MODEL 2182A') > 0:
            # print('Found Keithley 2182A at GPIB 7. Nano Voltmeter')
            pass
        else:
            print('Did NOT find 2181A at GPIB 7!!!!!!')
            found_all = False

        try:
            lock_in_id = self.lock_in.read_software_version()
        except Gpib.gpib.GpibError:
            lock_in_id = ''
        if lock_in_id.find('SR830') > 0:
            # print('Found SRS 830 at GPIB 8. Lock-In amplifier')
            pass
        else:
            print('Did NOT find SRS 830 at GPIB 8!!!')
            found_all = False

        try:
            current_source_id = self.current_source.read_software_version()
        except Gpib.gpib.GpibError:
            current_source_id = ''
        if current_source_id.find('MODEL 6221') > 0:
            # print('Found Keithley 6221 at GPIB 12. Current source')
            pass
        else:
            print('Did NOT find 6221 at GPIB 12!!!!!!')
            found_all = False

        try:
            dmm_id = self.dmm.read_software_version()
        except Gpib.gpib.GpibError:
            dmm_id = ''
        if dmm_id.find('MODEL 2000') > 0:
            # print('Found Keithley 2000 at GPIB 16. General purpose DMM')
            pass
        else:
            print('Did NOT find Keithley 2000 at GPIB 16!!!')
            found_all = False

        try:
            back_gate_id = self.back_gate.read_software_version()
        except Gpib.gpib.GpibError:
            back_gate_id = ''
        # todo: Also check S/N to verify correct instrument is connected
        if back_gate_id.find('MODEL 2400') > 0:
            # print('Found Keithley 2400 at GPIB 22. Use for Back Gate')
            pass
        else:
            print('Did NOT find Keithley 2400!!! No Back Gate!!!')
            found_all = False
        return found_all

    def _scan_gpib(self):
        for i in range(0, 30):
            device = Gpib.Gpib(0, pad=i)
            try:
                device.write('*IDN?')
            except Gpib.gpib.GpibError:
                continue
            reply = device.read()
            print('{}: {}'.format(i, reply))

    def instrument_id(self):
        found_all = self._identify_all_instruments()
        if not found_all:
            self._scan_gpib()

    def set_lock_in_frequency(self, frequency: float):
        self.lock_in_frequency = frequency
        # TODO: Configure SR830 with suitable time-constants
        return frequency

    def reset_current_measurement(self, measurement_type, error=False):
        """
        Reset current data if a new measurement is about to start.
        If measurement_type is None, this indicates that the measurement
        stops, in this case keep the data for now.
        """
        if measurement_type is None:
            self.current_measurement['type'] = None
            self.current_measurement['type'] = error
        else:
            for key, value in self.current_measurement.items():
                if isinstance(value, list):
                    self.current_measurement[key].clear()
            self.current_measurement.update(
                {
                    'type': measurement_type,
                    'start_time': time.time(),
                    'current_time': time.time()
                }
            )
        return True

    def add_to_current_measurement(self, data_point: dict):
        """
        Here we store the data, both permenantly in the database
        and temporarely in the local dict self.current_measurement
        """
        print(self.current_measurement['current'])
        now = time.time() - self.current_measurement['start_time']
        for key in self.current_measurement.keys():
            if key in data_point:
                value = data_point[key]
                self.current_measurement[key].append((now, value))
                self.data_set_saver.save_point(key, (now, value))
        self.current_measurement['current_time'] = time.time()

    def _add_metadata(self, labels, meas_type, comment, timestep=None, freq=None):
        metadata = {
            'Time': CustomColumn(time.time(), "FROM_UNIXTIME(%s)"),
            'label': None,
            'type': meas_type,
            'comment': comment,
            'timestep': timestep,
            'frequency': freq
        }
        for key, value in labels.items():
            metadata.update({'label': value})
            self.data_set_saver.add_measurement(key, metadata)
        return True

    def abort_measurement(self):
        print('ABORT')
        self.reset_current_measurement(None, error='Aborted')

    def _check_I_source_status(self):
        """
        Check that current source is operating as expected
        if not, the measurement has to be stopped.
        """
        source_ok = self.current_source.read_status()
        if not source_ok:
            print('ABORT DUE TO COMPLIENCE')
            self.reset_current_measurement(None, error=True)
            self.current_source.stop_and_unarm()
            self.current_source.set_current(0)
            self.current_source.output_state(False)
            print(self.current_source.latest_error)
        return source_ok

    def _calculate_steps(self, start, stop, steps, step_type='linear'):
        delta_current = stop - start
        step_size = delta_current / (steps - 1)
        step_list = []
        for i in range(0, steps):
            current = start + step_size * i
            step_list.append(current)
        # yield?
        return step_list

    def dc_4_point_measurement(self, start: float, stop: float, steps: int):
        """
        Perform a 4-point DC iv-measurement.
        :param start: The lowest current in the sweep.
        :param stop: The highest current in the sweep.
        :steps: Number of steps in the sweep.
        """
        # TODO!!! Take the comment as a parameter
        labels = {'v_total': 'Vtotal', 'v_sample': 'Vsample', 'current': 'Current'}
        self._add_metadata(labels, 201, 'DC measurement', timestep=0.2)
        self.reset_current_measurement('dc_sweep')
        # todo: If software-timed sweep is not good enough, look into sweeping 6221

        # Configure instruments:
        self.current_source.set_voltage_limit(1)
        self.current_source.set_current_range(stop)
        self.current_source.set_current(0)
        self.current_source.output_state(True)
        self.nanov1.set_range(0, 0)
        self.nanov1.set_integration_time(2)

        for current in self._calculate_steps(start, stop, steps):
            if self.current_measurement['type'] is None:
                # Measurement has been aborted, skip through the
                # rest of the steps
                continue

            self.current_source.set_current(current)
            time.sleep(0.02)
            if not self._check_I_source_status():
                return
            v_total = self.nanov1.read_voltage(1)
            v_sample = self.nanov1.read_voltage(2)
            data = {'current': current, 'v_total': v_total, 'v_sample': v_sample}
            self.add_to_current_measurement(data)
        # Indicate that the measurement is completed
        self.current_source.output_state(False)
        self.reset_current_measurement(None)

    def _ac_4_point_sweep(self, steps):
        """
        Perform an actual ac-sweep. Typically this will happen as a part
        of a larger sweep of some other parameter, could be gate voltage,
        magnetic field or temperature.
        """
        # todo: If software-timed sweep is not good enough, look into sweeping 6221
        time.sleep(1)
        for current in steps:
            # The current source use peak height as unit, everything
            # else use rmd, multiply by sqrt(2) to unify
            self.current_source.set_wave_amplitude(current * 1.4142)
            # Wait for ~10 cycles to ensure everything is settled
            time.sleep(10.0 / self.lock_in_frequency)
            if not self._check_I_source_status():
                return

            v_sample, _, _ = (self.lock_in.read_x_and_y())
            _, theta, _ = (self.lock_in.read_r_and_theta())
            v_total = self.dmm.next_reading()
            data = {'current': current, 'v_total': v_total,
                    'v_sample': v_sample, 'theta': theta}
            self.add_to_current_measurement(data)

    def _init_ac(self, start, stop):
        """
        Setup the current source for an AC measurement.
        :param start: This is the start value of the sweep and will be
        used a default amplitude until the actual measurement start.
        :param stop: The final value of the sweep, will be used to
        set the range.
        """
        self.current_source.stop_and_unarm()
        self.current_source.set_voltage_limit(1)
        self.current_source.set_current_range(stop)
        self.current_source.source_sine_wave(self.lock_in_frequency, start)
        return True

    def ac_4_point_measurement(self, start: float, stop: float, total_steps: int):
        """
        Perform a 4-point AC iv-measurement.
        :param start: The lowest current in the sweep.
        :param stop: The highest current in the sweep.
        :steps: Number of steps in the sweep.
        """
        labels = {'v_total': 'Vtotal', 'v_sample': 'Vsample',
                  'current': 'Current', 'theta': 'Theta'}
        self._add_metadata(labels, 202, 'AC measurement',
                           freq=self.lock_in_frequency)

        self.reset_current_measurement('ac_sweep')

        # self.dmm.read_ac_voltage()  # Configure DMM for AC measurement
        
        self._init_ac(start, stop)  # Configure current source
        time.sleep(1)

        current_steps = self._calculate_steps(start, stop, total_steps)
        t = threading.Thread(target=self._ac_4_point_sweep,
                             args=(current_steps,))
        t.start()
        while t.is_alive():
            if self.current_measurement['type'] is None:
                # Measurement has been aborted, skip through the
                # rest of the steps
                t.stop()

            print('waiting')
            time.sleep(1)
        # TODO!! Handle the case of non-succes!
        # if self.current_measurement['error']:

        # Indicate that the measurment is completed
        self.current_source.stop_and_unarm()
        self.reset_current_measurement(None)

    def _read_gate(self):
        voltage = self.back_gate.read_voltage()
        current = self.back_gate.read_current()
        data = {
            'v_backgate': voltage,
            'i_backgate': current
        }
        self.add_to_current_measurement(data)
        return current

    def gated_ac_4_point_measurement(
            self,
            i_start: float, i_stop: float, total_i_steps: int,
            backgate_from, backgate_to, gate_steps
    ):
        """
        Perform a gated 4-point AC iv-measurement.
        :param i_start: The lowest current in the sweep.
        :param i_stop: The highest current in the sweep.
        :param total_i_steps: Number of steps in the sweep.
        :param backgate_from:
        :param backgate_to:
        :param gate_steps:
        """
        labels = {
            'v_total': 'Vtotal', 'v_sample': 'Vsample',
            'current': 'Current', 'theta': 'Theta',
            'v_backgate': 'Back Gate Voltage', 'i_backgate': 'Back Gate Leak'
        }
        self._add_metadata(labels, 203, 'Gated AC measurement',
                           freq=self.lock_in_frequency)

        self.reset_current_measurement('gated_ac_sweep')

        # Todo: Set correct ranges for compliance and source
        self.back_gate.set_source_function('v')
        self.back_gate.set_current_limit(1e-4)
        self.back_gate.set_voltage(backgate_from)
        self.back_gate.output_state(True)
        time.sleep(0.1)
        self._read_gate()

        gate_steps = self._calculate_steps(backgate_from, backgate_to, gate_steps)

        self._init_ac(i_start, i_stop)  # Configure current source
        current_steps = self._calculate_steps(i_start, i_stop, total_i_steps)

        for gate_v in gate_steps:
            if self.current_measurement['type'] is None:
                continue
            self.back_gate.set_voltage(gate_v)
            time.sleep(0.5)
            self._read_gate()

            t = threading.Thread(target=self._ac_4_point_sweep,
                                 args=(current_steps,))
            t.start()
            while t.is_alive():
                if self.current_measurement['type'] is None:
                    # Measurement has been aborted
                    t.stop()

                # Backgate can be measured slower than the inner sweep,
                # we do it periodically while waiting for the sweep
                print('waiting')
                time.sleep(1)
                self._read_gate()
            self._read_gate()

        # TODO!! Handle the case of non-succes!
        # if self.current_measurement['error']:

        # Indicate that the measurment is completed
        self.current_source.stop_and_unarm()
        self.back_gate.set_voltage(0)
        self.back_gate.output_state(False)
        self.reset_current_measurement(None)

    def test(self):
        # self.instrument_id()
        # self.dc_4_point_measurement(1e-6, 1e-4, 100)
        # self.ac_4_point_measurement(1e-6, 1e-4, 100)
        self.ac_4_point_measurement(1e-8, 1e-7, 100)
        # self.gated_ac_4_point_measurement(1e-7, 1e-5, 100, 0, 10, 10)


if __name__ == '__main__':
    cm = CrystatMeasurement()
    cm.test()
