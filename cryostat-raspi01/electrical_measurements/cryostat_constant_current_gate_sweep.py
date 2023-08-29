import time

import numpy as np

from cryostat_measurement_base import CryostatMeasurementBase
from cryostat_dc_base import CryostatDCBase


class CryostatConstantCurrentGateSweep(CryostatDCBase):
    def __init__(self):
        super().__init__()

    def _calculate_steps(self, v_low, v_high, steps, repeats):
        """ This code is also used in the Linkham code """
        delta = v_high - v_low
        step_size = delta / (steps - 1)

        # From 0 to v_high
        up = list(np.arange(0, v_high, step_size))
        # v_high -> 0
        down = list(np.arange(v_high, 0, -1 * step_size))

        # N * (v_high -> v_low -> v_high)
        zigzag = (
            list(np.arange(v_high, v_low, -1 * step_size)) +
            list(np.arange(v_low, v_high, step_size))
        ) * repeats
        step_list = up + zigzag + down + [0]
        return step_list

    def _configure_source(self, v_limit, current):
        """
        Configure current source
        todo: This might belong in DC Base
        """
        self.current_source.set_voltage_limit(v_limit)
        self.current_source.set_current_range(current)
        self.current_source.set_current(0)
        self.current_source.output_state(True)

    def _configure_dmm(self, v_limit):
        """
        Configure  Model 2000 used for 2-point measurement
        The unit is set up to measure on the buffered guard output of
        the 6221.
        todo: This might belong in DC Base
        """
        self.dmm.configure_measurement_type('volt:dc')
        self.dmm.set_range(v_limit)
        self.dmm.set_integration_time(2)
        # TODO: Replace the line below with a line that configures a trigger
        self.dmm.scpi_comm(':INIT:CONT ON')  # TODO: Add this to driver

    def _configure_nano_voltmeters(self, nplc):
        """
        Confgire the 2182a's for voltage measurement
        todo: This might belong in DC Base
        todo: Setup for external triggering (now done via frontpanel)
        todo: accept other range than auto-range
        """
        self.current_source._2182a_comm(':SENSE:VOLT:CHANNEL1:RANGE:AUTO ON')
        self.xy_nanov.set_range(0, 0)
        self.current_source._2182a_comm('SENSE:VOLTAGE:NPLCYCLES ' + str(nplc))
        self.xy_nanov.set_integration_time(nplc)
        self.current_source._2182a_comm()

    def _configure_back_gate(self):
        """
        Confgire the 2400 for gating
        todo: This might belong in DC Base
        """
        self.back_gate.set_source_function('v')
        self.back_gate.set_current_limit(1e-4)
        self.back_gate.set_voltage(0)
        self.back_gate.output_state(True)

    def abort_measurement(self):
        print('ABORT')
        self.reset_current_measurement(None, error='Aborted')

    def constant_current_gate_sweep(
            self, comment, current: float, v_low: float, v_high: float,
            steps: int, repeats: int, v_limit: int = 1, nplc: int = 5,
            **kwargs
    ):
        """
        Perform a gate sweep while holding a fixed current. Measure voltage.
        TODO:
        * Integration time for backgate should be configurable
        * Source-measure delay should be configurable and stored as metadata
        """
        labels = {
            'v_backgate': 'Gate voltage', 'i_backgate': 'Gate current',
            'b_field': 'B-Field', 'vti_temp': 'VTI Temperature',
            'sample_temp': 'Sample temperature'
        }
        self._add_metadata(labels, 208, comment)
        labels = {'v_total': 'Vtotal'}
        self._add_metadata(labels, 208, comment, current=current)
        labels = {'v_xx': 'Vxx', 'v_xy': 'Vxy'}
        self._add_metadata(labels, 208, comment, current=current, nplc=nplc)
        self.reset_current_measurement('dc_gate_sweep')

        # Configure instruments:
        self._configure_source(v_limit=v_limit, current=current)
        self._configure_dmm(v_limit=v_limit)
        self._configure_nano_voltmeters(nplc)
        self._configure_back_gate()

        # Set the constant current level
        self.current_source.set_current(current)
        time.sleep(0.1)
        if not self._check_I_source_status():
            return

        time.sleep(0.1)
        self._read_gate()

        aborted = False
        for gate_v in self._calculate_steps(v_low, v_high, steps, repeats):
            if self.current_measurement['type'] is None:
                # Measurement has been aborted, skip through the
                # rest of the steps
                aborted = True
                continue

            self.back_gate.set_voltage(gate_v)
            # Source measure dealy:
            time.sleep(0.001)  # TODO: Make the delay configurable
            data = self._read_voltages(nplc)

            self.add_to_current_measurement(data)
            self._read_cryostat()

        if aborted:
            gate_v = self.back_gate.read_voltage()
            steps = np.arange(gate_v, 0, -0.2 * np.sign(gate_v))
            for gate_v in steps:
                self.back_gate.set_voltage(gate_v)
                time.sleep(0.001)  # TODO: Make the delay configurable
                data = self._read_voltages(nplc)
                self.add_to_current_measurement(data)

        time.sleep(2)
        # Indicate that the measurement is completed
        self.current_source.output_state(False)
        self.reset_current_measurement(None)

    def test(self):
        # self.instrument_id()
        self.constant_current_gate_sweep(
            comment='Test measurement',
            current=3e-6,
            v_low=-5,
            v_high=5,
            v_limit=1.7,
            steps=15,
            repeats=2,
        )


if __name__ == '__main__':
    ccgs = CryostatConstantCurrentGateSweep()
    ccgs.test()
