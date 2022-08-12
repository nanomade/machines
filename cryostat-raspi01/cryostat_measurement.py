import time
import logging

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
    'start_time': 0,
    'current_time': 0,
    'current': [],
    'v_total': [],
    'v_sample': [],
    'v_gate': []
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
        self.data_set_saver = DataSetSaver("measurements_" + self.chamber_name,
                                           "xy_values_" + self.chamber_name,
                                           credentials.user, credentials.passwd)
        self.data_set_saver.start()
        

    def _identify_all_instruments(self):
        found_all = True
        nanov1_id = self.nanov1.read_software_version()
        if nanov1_id.find('MODEL 2182A') > 0:
            # print('Found Keithley 2182A at GPIB 7. Nano Voltmeter')
            pass
        else:
            print('Did NOT find 2181A at GPIB 7!!!!!!')
            found_all = False
        
        lock_in_id = self.lock_in.read_software_version()
        if lock_in_id.find('SR830') > 0:
            # print('Found SRS 830 at GPIB 8. Lock-In amplifier')
            pass
        else:
            print('Did NOT find SRS 830 at GPIB 8!!!')
            found_all = False

        current_source_id = self.current_source.read_software_version()
        if current_source_id.find('MODEL 6221') > 0:
            # print('Found Keithley 6221 at GPIB 12. Current source')
            pass
        else:
            print('Did NOT find 6221 at GPIB 12!!!!!!')
            found_all = False
            
        dmm_id = self.dmm.read_software_version()
        if dmm_id.find('MODEL 2000') > 0:
            # print('Found Keithley 2000 at GPIB 16. General purpose DMM')
            pass
        else:
            print('Did NOT find Keithley 2000 at GPIB 16!!!')
            found_all = False

        back_gate_id = self.back_gate.read_software_version()
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

    def reset_current_measurement(self, measurement_type):
        """
        Reset current data if a new measurement is about to start.
        If measurement_type is None, this indicates that the measurement
        stops, in this case keep the data for now.
        """
        if measurement_type is None:         
            self.current_measurement['type'] = None
        else:
            self.current_measurement = CURRENT_MEASUREMENT_PROTOTYPE.copy()
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
                self.current_measurement[key].append(value)
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

    def _check_I_source_status(self):
        """
        Check that current source is operating as expected
        if not, the measurement has to be stopped.
        """
        source_ok = self.current_source.read_status()
        if not source_ok:
            print('ABORT')
            self.reset_current_measurement(None)
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
            self.current_source.set_current(current)
            print(current)
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

    def ac_4_point_measurement(self, start: float, stop: float, steps: int):
        """
        Perform a 2-point DC iv-measurement.
        :param start: The lowest current in the sweep.
        :param stop: The highest current in the sweep.
        :steps: Number of steps in the sweep.
        """
        FREQ = 1976
        labels = {'v_total': 'Vtotal', 'v_sample': 'Vsample',
                  'current': 'Current', 'theta': 'Theta'}
        self._add_metadata(labels, 202, 'AC measurement', timestep=0.02, freq=FREQ)
            
        self.reset_current_measurement('ac_sweep')
        # # todo: If software-timed sweep is not good enough, look into sweeping 6221

        # # Configure instruments:
        self.current_source.stop_and_unarm()
        self.current_source.set_voltage_limit(1)
        self.current_source.set_current_range(stop)
        self.current_source.source_sine_wave(FREQ, start)
        
        for current in self._calculate_steps(start, stop, steps):
            # The current source use peak height as unit, everything
            # else use rmd, multiply by sqrt(2) to unify
            self.current_source.set_wave_amplitude(current * 1.4142)
            time.sleep(0.02)
            if not self._check_I_source_status():
                return

            v_sample, _, _ = (self.lock_in.read_x_and_y())
            _, theta, _ = (self.lock_in.read_r_and_theta())
            v_total = self.dmm.next_reading()
            data = {'current': current, 'v_total': v_total,
                    'v_sample': v_sample, 'theta': theta}
            self.add_to_current_measurement(data)

        # Indicate that the measurment is completed
        self.current_source.stop_and_unarm()
        self.reset_current_measurement(None)

        
    def test(self):
        self.instrument_id()
        # self.dc_4_point_measurement(1e-6, 1e-4, 100)
        self.ac_4_point_measurement(1e-6, 1e-4, 100)


if __name__ == '__main__':
    cm = CrystatMeasurement()
    cm.test()
