import time

from cryostat_measurement_base import CryostatMeasurementBase
from cryostat_dc_base import CryostatDCBase


class CryostatConstantCurrentGateSweep(CryostatDCBase):
    def __init__(self):
        super().__init__()

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
        # TODO: Add v_limit as metadata
        labels = {'v_total': 'Vtotal'}
        self._add_metadata(labels, 208, comment, current=current)
        labels = {'v_xx': 'Vxx', 'v_xy': 'Vxy'}
        self._add_metadata(labels, 208, comment, current=current, nplc=nplc)
        self.reset_current_measurement('dc_gate_sweep')

        # Configure instruments:
        self._configure_source(v_limit=v_limit, current_range=current)
        self._configure_dmm(v_limit=v_limit)
        self._configure_nano_voltmeters(nplc)
        self._configure_back_gate()

        # Set the constant current level
        self.current_source.set_current(current)
        time.sleep(0.1)
        if not self._check_I_source_status():
            return

        time.sleep(0.1)
        self.read_gate()

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

            print('Data ', data)
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
