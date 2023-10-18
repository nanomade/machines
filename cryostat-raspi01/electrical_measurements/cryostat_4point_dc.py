import time

from cryostat_dc_base import CryostatDCBase


class Cryostat4PointDC(CryostatDCBase):
    def __init__(self):
        super().__init__()

    def abort_measurement(self):
        print('ABORT')
        self.reset_current_measurement(None, error='Aborted')

    def dc_4_point_measurement(
            self, comment, start: float, stop: float, steps: int,
            v_limit: float = 1.0, nplc: float = 1, gate_v: float = None, **kwargs
    ):
        """
        Perform a 4-point DC iv-measurement.
        :param start: The lowest current in the sweep
        :param stop: The highest current in the sweep
        :param steps: Number of steps in sweep
        :param nplc: Integration time of voltage measurements
        :params gate_v: Optional gate voltage at which the sweep is performed
        :v_limit: Maximal allowed voltage, default is 1.0
        """
        labels = {
            'v_total': 'Vtotal', 'current': 'Current', 'v_backgate': 'Gate voltage',
            'i_backgate': 'Gate current', 'b_field': 'B-Field',
            'vti_temp': 'VTI Temperature', 'sample_temp': 'Sample temperature'
        }
        self._add_metadata(labels, 201, comment)
        labels = {'v_xx': 'Vxx', 'v_xy': 'Vxy'}
        self._add_metadata(labels, 201, comment, nplc=nplc)
        self.reset_current_measurement('dc_sweep')

        # Configure instruments:
        self._configure_back_gate()  # Also used to trigger 2182a's
        if gate_v is not None:
            self.back_gate.set_voltage(gate_v)

        self._configure_dmm(v_limit)  # SET DMM TO TAKE EXTERNAL TRIGGER
        self._configure_source(v_limit=v_limit, current_range=stop)
        self._configure_nano_voltmeters(nplc)  # SET NVM TO TAKE EXTERNAL TRIGGER

        time.sleep(3)
        self.current_source.set_current(start)

        iteration = 0
        for current in self._calculate_steps(start, stop, steps):
            iteration += 1
            if self.current_measurement['type'] is None:
                # Measurement has been aborted, skip through the
                # rest of the steps
                continue

            self.current_source.set_current(current)
            time.sleep(0.05)
            if not self._check_I_source_status():
                return

            store_gate = False  # Store gate every 3 iterations if gate is used
            if iteration % 3 == 0:
                store_gate = (gate_v is not None)

            data = self._read_voltages(nplc, store_gate=store_gate)
            data['current'] = current
            print('Data: ', data)
            self.add_to_current_measurement(data)
            self._read_cryostat()

        time.sleep(2)
        # Indicate that the measurement is completed
        self.current_source.output_state(False)
        self.reset_current_measurement(None)

    def test(self):
        # self.instrument_id()
        self.dc_4_point_measurement(-1e-4, 1e-4, 100)


if __name__ == '__main__':
    cm = Cryostat4PointDC()
    cm.test()
