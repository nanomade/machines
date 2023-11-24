import time
import numpy as np
from ps_dc_base import ProbeStationDCBase


class ProbeStation4PointDC(ProbeStationDCBase):
    def __init__(self):
        # super().__init__(self=self)
        super().__init__()

        # Todo: Maybe this belongs in all configurations
        time.sleep(0.2)

    def abort_measurement(self):
        print('ABORT')
        self.reset_current_measurement(None, error='Aborted')

    def dc_4_point_measurement(
        self,
        comment,
        start: float,
        stop: float,
        steps: int,
        i_limit: float = 1.0e-6,
        nplc: float = 1,
        gate_v: float = 0,
        gate_limit: float = -1e-8,
        **kwargs
    ):
        """
        Perform a 4-point DC vi-measurement.
        :param start: The lowest voltage in the sweep
        :param stop: The highest voltage in the sweep
        :param steps: Number of steps in sweep
        :param nplc: Integration time of  measurements
        :params gate_v: Optional gate voltage at which the sweep is performed
        :v_limit: Maximal allowed voltage, default is 1.0
        """
        labels = {
            'v_total': 'Vtotal',
            'current': 'Current',
            'v_backgate': 'Gate voltage',
            'i_backgate': 'Gate current',
        }
        self._add_metadata(labels, 201, comment)
        labels = {'v_xx': 'Vxx'}  # Vxy is not currently supported
        self._add_metadata(labels, 201, comment, nplc=nplc)
        self.reset_current_measurement('dc_sweep')

        # Configure instruments:
        print('CONFIGURE')
        print('Back gate')
        self._configure_back_gate(source_range=gate_v, current_limit=gate_limit)
        print('DMM')
        self._configure_dmm(v_limit=stop)
        print('Source')
        source_range = max(abs(start), abs(stop))
        self._configure_source(source_range=source_range, current_limit=i_limit)
        print('CONFIGURE - DONE')
        print()

        # Ramp to selected gate voltage
        ramp_list = list(np.arange(0, gate_v, 0.05 * np.sign(gate_v))) + [gate_v]
        for gate_ramp_v in ramp_list:
            print('Ramping gate to {}'.format(gate_ramp_v))
            self.back_gate.set_voltage(gate_ramp_v)
            self.read_gate()
            self.read_source()
            time.sleep(0.5)

        time.sleep(2)
        self.source.set_voltage(start)
        time.sleep(1)

        iteration = 0
        for voltage in self._calculate_steps(start, stop, steps):
            if self.current_measurement['type'] is None:
                # Measurement has been aborted, skip through the
                # rest of the steps
                continue

            print('Set source to: ', voltage)
            self.source.set_voltage(voltage)
            time.sleep(0.05)
            if not self._check_I_source_status():
                # TODO!!! This always returns True!!!!
                return

            self.read_source()  # Also reads 2-point via the DMM
            self.read_gate()

        time.sleep(2)

        # Ramp gate back to zero
        ramp_list.reverse()
        for gate_ramp_v in ramp_list:
            print('Ramping gate to {}'.format(gate_ramp_v))
            self.back_gate.set_voltage(gate_ramp_v)
            self.read_gate()
            self.read_source()
            time.sleep(0.5)

        # Indicate that the measurement is completed
        self.back_gate.output_state(False)
        self.source.output_state(False)
        self.reset_current_measurement(None)

    def test(self):
        # self.instrument_id()
        self.dc_4_point_measurement(
            comment='test()',
            start=-1e-4,
            stop=1e-4,
            steps=50,
            i_limit=1.0e-6,
            nplc=1,
            gate_v=-1,
            gate_limit=-1e-6,
        )


if __name__ == '__main__':
    ps = ProbeStation4PointDC()
    ps.test()
