"""
Perform a constant-current DC measurement using one (or in the future two)
Keithley 2182's and the 6221 current source. No gate is involved in this
measurement.
"""
import time

from PyExpLabSys.drivers.keithley_2182 import Keithley2182
from cryostat_measurement_base import CryostatMeasurementBase


class CryostatConstantCurrent(CryostatMeasurementBase):
    def __init__(self):
        super().__init__()
        self.nanov1 = Keithley2182(
            interface='serial',
            device='/dev/serial/by-id/usb-1a86_USB2.0-Ser_-if00-port0',
        )

    def abort_measurement(self):
        print('ABORT')
        self.reset_current_measurement(None, error='Aborted')

    def constant_current(
            self, comment: str, current: float, measure_time: float,
            v_limit: float = 1, gate_v: float = None, **kwargs
    ):
        """
        Perform a simple constant-current measurement. This could be used as either
        a very simple test measurement, or to track perfomance as function of a
        non-electric parameter souch as temperature or magnetic field.
        :param comment: Comment for the measurement
        :param current: Probe current
        :param measure_time: The amount of time for the measurement to run
        :param gate_v: Constant gate voltage during measurement
        :param **kwargs: Used to absorb extra args from network syntax
        """
        labels = {
            'v_total': 'Vtotal',
            'v_xx': 'Vxx',
            'b_field': 'B-Field',
            'sample_temp': 'Sample Temperature',
            'vti_temp': 'VTI Temperature',
        }
        # TODO: Add v_limit as metadata
        self._add_metadata(labels, 220, comment, current=current)
        self.reset_current_measurement('delta_constant_current')

        # Allow the main loop to release DMM
        time.sleep(1)
        self.dmm.set_trigger_source(external=False)
        time.sleep(1)
        self.dmm.set_range(v_limit)
        time.sleep(1)
        self.dmm.set_integration_time(10)

        self.nanov1.set_integration_time(10)
        self.nanov1.set_trigger_source(external=False)
        # Trigger a single measurement, all other measurements will be
        # read_fresh()
        self.nanov1.read_voltage(1)
        

        if gate_v is not None:
            self._configure_back_gate()
            self.back_gate.set_voltage(gate_v)

        self.current_source.set_voltage_limit(v_limit)
        self.current_source.set_current(current)
        self.current_source.output_state(True)
        time.sleep(3.0)

        t_start = time.time()
        while (time.time() - t_start) < measure_time:
            self._read_cryostat()
            time.sleep(0.1) # Sleep should be approximately equal to
            # integration time of v_total and v_xx
            v_xx = self.nanov1.read_fresh()
            v_total = self.dmm.next_reading()

            if self.current_measurement['type'] is None:
                break
            data = {'v_xx': v_xx, 'v_total': v_total}
            print(data)
            self.add_to_current_measurement(data)

        self.current_source.set_current(0)
        time.sleep(2)
        self.current_source.output_state(False)

        if gate_v is not None:
            self.back_gate.set_voltage(0)

        time.sleep(5)
        self.reset_current_measurement(None)

    def test(self):
        self.constant_current(
            'Test run', current=1e-3, measure_time=120, v_limit=0.95, gate_v=None
        )


if __name__ == '__main__':
    ccc = CryostatConstantCurrent()
    ccc.test()
