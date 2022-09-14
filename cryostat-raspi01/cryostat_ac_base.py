import time
# import logging

from PyExpLabSys.drivers.srs_sr830 import SR830
from cryostat_measurement_base import CryostatMeasurementBase


class CryostatACBase(CryostatMeasurementBase):
    def __init__(self):
        super().__init__()
        # self.dmm and self.current_source are always in the base
        self.lock_in = SR830(interface='gpib', gpib_address=8)
        self.set_lock_in_frequency(1010.0)

    def set_lock_in_frequency(self, frequency: float):
        self.lock_in_frequency = frequency
        # TODO: Configure SR830 with suitable time-constants
        return frequency

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
            # time.sleep(0.1)

            if not self._check_I_source_status():
                return

            # _, theta, _ = self.lock_in.read_r_and_theta()
            v_sample, theta, _ = self.lock_in.read_r_and_theta()

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
        # self.dmm.set_range(1)  # Complience value of AC source is 1V pk-pk
        self.current_source.stop_and_unarm()
        self.current_source.set_voltage_limit(1)
        self.current_source.set_current_range(stop)
        self.current_source.source_sine_wave(self.lock_in_frequency, start * 1.4142)
        return True
