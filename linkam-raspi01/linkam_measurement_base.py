import time
# import logging
import threading

import Gpib  # linux-gpib, user space wrapper to kernel driver

from PyExpLabSys.drivers.srs_sr830 import SR830
from PyExpLabSys.drivers.keithley_2000 import Keithley2000
from PyExpLabSys.drivers.keithley_2400 import Keithley2400
# Todo: Check why CustomColumn is needed???
from PyExpLabSys.common.database_saver import DataSetSaver, CustomColumn

import credentials


CURRENT_MEASUREMENT_PROTOTYPE = {
    'type': None,  # DC-sweep, AC-sweep
    'error': None,
    'start_time': 0,
    'current_time': 0,
    'theta_1': [],
    'theta_2': [],
    'current_1': [],
    'current_2': [],
    'lock_in_v1': [],
    'lock_in_v2': [],
    'v_backgate': [],  # Back gate voltage
    'i_backgate': []  # Bakc gate leak-current
}


class LinkamMeasurementBase(object):
    def __init__(self):
        self.current_measurement = CURRENT_MEASUREMENT_PROTOTYPE.copy()
        self.lock_in_1 = SR830(interface='gpib', gpib_address=7)
        self.lock_in_2 = SR830(interface='gpib', gpib_address=6)
        self.back_gate = Keithley2400(interface='gpib', gpib_address=22)
        self.source_logger_1 = Keithley2000(interface='gpib', gpib_address=14)
        self.source_logger_2 = Keithley2000(interface='gpib', gpib_address=15)

        self.chamber_name = "dummy"
        self._restart_data_set_saver()

    def _restart_data_set_saver(self):
        self.data_set_saver = DataSetSaver("measurements_" + self.chamber_name,
                                           "xy_values_" + self.chamber_name,
                                           credentials.user, credentials.passwd)
        self.data_set_saver.start()

    # Todo, take arguments to check only the needed instruments, or
    # check each instrument but report error only if it is not None
    def _identify_all_instruments(self):
        found_all = True
        try:
            lock_in_1_id = self.lock_in_1.read_software_version()
        except Gpib.gpib.GpibError:
            lock_in_1_id = ''
        if lock_in_1_id.find('SR830') > 0:
            print('Found SRS 830 at GPIB 7. Lock-In amplifier')
        else:
            print('Did NOT find SR830 at GPIB 7 - LockIn 1 missing!!!!!!')
            found_all = False

        try:
            lock_in_2_id = self.lock_in_2.read_software_version()
        except Gpib.gpib.GpibError:
            lock_in_2_id = ''
        if lock_in_2_id.find('SR830') > 0:
            print('Found SRS 830 at GPIB 6. Lock-In amplifier')
        else:
            print('Did NOT find SR830 at GPIB 6 - LockIn 2 missing!!!!!!')
            found_all = False

        try:
            source_logger_1_id = self.source_logger_1.read_software_version()
        except Gpib.gpib.GpibError:
            source_logger_1_id = ''
        if source_logger_1_id.find('MODEL 2000') > 0:
            print('Found Keithley 2000 at GPIB 14. source_logger_1')
            # pass
        else:
            print('Did NOT find Keithley 2000 at GPIB 14, no source_logger_1!!!')
            found_all = False

        try:
            source_logger_2_id = self.source_logger_2.read_software_version()
        except Gpib.gpib.GpibError:
            source_logger_2_id = ''
        if source_logger_2_id.find('MODEL 2000') > 0:
            print('Found Keithley 2000 at GPIB 15. source_logger_2')
            # pass
        else:
            print('Did NOT find Keithley 2000 at GPIB 15, no source_logger_2!!!')
            found_all = False

        try:
            back_gate_id = self.gate.read_software_version()
        except Gpib.gpib.GpibError:
            back_gate_id = ''
        if back_gate_id.find('MODEL 2400') > 0:
            print('Found Keithley 2400 at GPIB 22. Use for Gate')
            pass
        else:
            print('Did NOT find Keithley 2400!!! No Gate!!!')
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
        # Will be re-implemented in AC classes
        pass

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
        now = time.time() - self.current_measurement['start_time']
        for key in self.current_measurement.keys():
            if key in data_point:
                value = data_point[key]
                self.current_measurement[key].append((now, value))
                self.data_set_saver.save_point(key, (now, value))
        self.current_measurement['current_time'] = time.time()

    def _add_metadata(self, labels, meas_type, comment, timestep=None, freq=None):
        # Test that the sql-connection is still alive - if it fails, this would be
        # a good chance to restart.
        # Print is only for debuging, should be replaced with try-except
        try:
            # Test if sql-connection is still alive
            self.data_set_saver.get_unique_values_from_measurements('type')
        except self.data_set_saver.MySQLdb._exceptions.OperationalError:
            self._restart_data_set_saver()

        timestamp = CustomColumn(time.time(), "FROM_UNIXTIME(%s)")
        for key, value in labels.items():
            metadata = {
                'Time': timestamp,
                'label': None,
                'type': meas_type,
                'comment': comment,
                'timestep': timestep,
                'frequency': freq
            }

            if isinstance(value, str):
                metadata.update({'label': value})
            else:  # value is dict
                metadata.update(value)

            self.data_set_saver.add_measurement(key, metadata)
        return True

    def abort_measurement(self):
        print('ABORT')
        self.reset_current_measurement(None, error='Aborted')

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


if __name__ == '__main__':
    Base = LinkamMeasurementBase()
    # Base._identify_all_instruments()
    Base._scan_gpib()
