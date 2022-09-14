import time

from PyExpLabSys.drivers.keithley_2182 import Keithley2182
from cryostat_measurement_base import CryostatMeasurementBase


class Cryostat4PointDC(CryostatMeasurementBase):
    def __init__(self):
        super().__init__()
        # self.dmm and self.current_source are always in the base
        self.nanov1 = Keithley2182(interface='gpib', gpib_address=7)

    def abort_measurement(self):
        print('ABORT')
        self.reset_current_measurement(None, error='Aborted')

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
        self.nanov1.set_integration_time(10)

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

    def test(self):
        # self.instrument_id()
        self.dc_4_point_measurement(1e-6, 1e-5, 100)


if __name__ == '__main__':
    cm = Cryostat4PointDC()
    cm.test()
