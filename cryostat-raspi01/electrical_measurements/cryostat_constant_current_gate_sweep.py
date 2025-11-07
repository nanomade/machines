import time

from cryostat_measurement_base import CryostatMeasurementBase
from cryostat_dc_base import CryostatDCBase


class CryostatConstantCurrentGateSweep(CryostatDCBase):
    def __init__(self):
        # Trigger all instruments, no hurt in also triggering non-used instruments
        trigger_list = [
            1,  # Vxy - white
            2,  # DMM - brown
            3,  # Vxx - Green
            4,  # Osciloscope - Yellow
        ]
        super().__init__(trigger_list)

    def abort_measurement(self):
        print('ABORT')
        self.reset_current_measurement(None, error='Aborted')

    def constant_current_gate_sweep(
            self, comment, current: float, back_gate: dict, front_gate: dict = None,
            v_limit: float = 1, nplc: int = 5, **kwargs
    ):
        """
        Perform a gate sweep while holding a fixed current. Measure voltage.
        TODO:
        * Source-measure delay should be configurable and stored as metadata
        """
        labels = {
            'v_backgate': 'Back Gate voltage', 'i_backgate': 'Back Gate current',
            'b_field': 'B-Field', 'vti_temp': 'VTI Temperature',
            'sample_temp': 'Sample temperature'
        }
        self._add_metadata(labels, 208, comment)
        if front_gate:
            labels = {
                'v_frontgate': 'Front Gate voltage', 'i_frontgate': 'Front Gate current',
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

        if front_gate:
            self.configure_front_gate()
        else:
            self.front_gate = None

        self.configure_back_gate()

        # Set the constant current level
        self.current_source.set_current(current)
        time.sleep(0.1)
        if not self._check_I_source_status():
            return

        time.sleep(0.1)
        self.read_gate()

        aborted = False
        back_gate_steps = self._calculate_steps(
            back_gate['v_low'], back_gate['v_high'],
            back_gate['steps'], back_gate['repeats']
        )
        for back_gate_v in back_gate_steps:
            if self.current_measurement['type'] is None:
                # Measurement has been aborted, skip through the rest of the steps
                aborted = True
                continue

            self.back_gate.set_voltage(back_gate_v)
            # Source measure dealy:
            time.sleep(0.05)  # TODO: Make the delay configurable

            # Trigger both the measurment on the 2540 and the voltmeters
            self.back_gate.trigger_measurement()
            if self.front_gate:  # TODO: Can we do this via a digital line?
                self.front_gate.trigger_measurement()

            t = time.time()
            self.read_gate()
            t_gate = 1000 * (time.time() - t)

            t = time.time()
            data = self._read_voltages(nplc)
            t_voltages = 1000 * (time.time() - t)
            # print('Gate: {:.0f}ms. Voltages: {:.0f}ms.'.format(t_gate, t_voltages))
            self.add_to_current_measurement(data)
            self._read_cryostat()

        if aborted:
            # TODO!!! read_voltage() HAS CHANGED SYNTAX!
            back_gate_v = self.back_gate.read_voltage()
            steps = np.arange(gate_v, 0, -0.2 * np.sign(back_gate_v))
            for back_gate_v in steps:
                self.back_gate.set_voltage(back_gate_v)
                time.sleep(0.001)  # TODO: Make the delay configurable
                data = self._read_voltages(nplc)
                self.add_to_current_measurement(data)

        time.sleep(2)
        # Indicate that the measurement is completed
        self.current_source.output_state(False)
        self.reset_current_measurement(None)

    def test(self):
        back_gate = {
            'v_low': -5,
            'v_high': 2,
            'steps': 41,
            'repeats': 1,
        }
        front_gate = True  # TEMPORARY, WILL BE A DICT!!!
        self.constant_current_gate_sweep(
            comment='Test measurement',
            current=3e-6,
            back_gate=back_gate,
            front_gate=front_gate,
            nplc=1,
        )


if __name__ == '__main__':
    ccgs = CryostatConstantCurrentGateSweep()
    ccgs.test()
