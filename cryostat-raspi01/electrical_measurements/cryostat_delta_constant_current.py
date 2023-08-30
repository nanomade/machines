import time

# from PyExpLabSys.drivers.keithley_2182 import Keithley2182
from cryostat_measurement_base import CryostatMeasurementBase


class CryostatDeltaConstantCurrent(CryostatMeasurementBase):
    def __init__(self):
        super().__init__()

    def abort_measurement(self):
        print('ABORT')
        self.reset_current_measurement(None, error='Aborted')

    def delta_constant_current(
            self, comment: str, current: float, v_limit: float = 1,
            measure_time: float = None, **kwargs
    ):
        """
        Perform a simple constant-current measurement. This could be used as either
        a very simple test measurement, or to track perfomance as function of a
        non-electric parameter souch as temperature or magnetic field.
        # TODO: Add option to set a static non-zero gate voltage
        :param comment: Comment for the measurement
        :param current: Probe current
        :param measure_time: The amount of time for the measurement to run
        :param **kwargs: Used to absorb extra args from network syntax
        """
        # TODO!!! Take the comment as a parameter
        labels = {
            'v_total': 'Vtotal',
            'v_xx': 'Vxx',
            'b_field': 'B-Field',
            'sample_temp': 'Sample Temperature',
            'vti_temp': 'VTI Temperature',
            # GATE!!!!!!!!!!!
        }
        self.dmm.set_trigger_source(external=True)
        self.dmm.set_range(v_limit)
        # Be fast enough to resolve the speed of delta mode
        self.dmm.set_integration_time(1)

        # TODO: Add v_limit as metadata
        self._add_metadata(labels, 207, comment, current=current)
        self.reset_current_measurement('delta_constant_current')

        # This should be handled by DMM in AC mode
        # two_wire_v = self.current_source.read_2182a_channel_2(current)
        # data = {'v_total': two_wire_v}
        # self.add_to_current_measurement(data)

        self.current_source.prepare_delta_measurement(current, v_limit)
        time.sleep(1.0)
        t_start = time.time()
        while (time.time() - t_start) < measure_time:
            self._read_cryostat()
            time.sleep(1.0)
            try:
                v_xx, meas_time = self.current_source.read_delta_measurement()
            except ValueError:
                print('Value error, not enough elements')
                continue

            v_xx = abs(v_xx)  # Not really sure how this can be negative...
            # This is measured at a random time in the delta interval and thus
            # has a random sign.
            # todo: Keep track of measurements and do delta here as well
            v_total = abs(self.dmm.next_reading())

            # todo: Measure gate current (when static gate V has been implemented)

            if self.current_measurement['type'] is None:
                break
            data = {'v_xx': v_xx, 'v_total': v_total}
            self.add_to_current_measurement(data)

        # Indicate that the measurement is completed
        self.current_source.end_delta_measurement()
        time.sleep(5)
        self.reset_current_measurement(None)

    def test(self):
        # self.instrument_id()
        self.delta_constant_current('Test run', 1e-3, 600)


if __name__ == '__main__':
    cdcc = CryostatDeltaConstantCurrent()
    cdcc.test()
