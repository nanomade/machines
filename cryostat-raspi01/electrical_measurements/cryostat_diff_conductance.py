import time

from cryostat_measurement_base import CryostatMeasurementBase


class CryostatDifferentialConductance(CryostatMeasurementBase):
    def __init__(self):
        super().__init__()

    def abort_measurement(self):
        print('ABORT')
        self.reset_current_measurement(None, error='Aborted')

    def differential_conductance_measurement(
            self, comment, start: float, stop: float, steps: int,
            delta: float, v_limit: float, nplc: float = 5, **kwargs
    ):
        """
        Perform a differential conductance measurement
        :param start: The lowest current in the sweep.
        :param stop: The highest current in the sweep.
        :steps: Number of steps in the sweep.
        # TODO: Add v_limit
        """
        labels = {
            # 'v_total': 'Vtotal',
            'dv_di': 'dV/dI', 'v_xx': 'Vxx', 'v_total': 'Vtotal',
            'current': 'Current', 'b_field': 'B-Field',
            'sample_temp': 'Sample Temperature', 'vti_temp': 'VTI Temperature'
        }

        # Configure dmm
        self.dmm.set_trigger_source(external=True)
        self.dmm.set_range(1.9)
        # Be fast enough to resolve the speed of delta mode
        self.dmm.set_integration_time(0.1)

        self._add_metadata(labels, 206, comment, timestep=0.2, delta_i=delta)
        self.reset_current_measurement('differential_conductance')

        self.current_source.perform_differential_conductance_measurement(
            start=start, stop=stop, steps=steps, delta=delta,
            v_limit=v_limit, nplc=nplc
        )
        self.current_source.read_diff_conduct_line()  # Discard first line
        err_count = 0
        for i in range(0, 100000):  # <- large number
            if self.current_measurement['type'] is None:
                # Measurement has been aborted - do something!
                break
            t = time.time()
            row = self.current_source.read_diff_conduct_line()
            print('Get row: {}'.format(time.time() - t))

            t = time.time()
            if row:
                data = {
                    'current': row['current'],
                    'v_xx': row['avoltage'],
                    'dv_di': row['reading'],
                }
                self.add_to_current_measurement(data)
            print('Added row: {}'.format(time.time() - t))

            # TODO! Find a better way to detect that the measurement has ended!
            # Possibly by counting rows if we trust we get all of them
            step_size = (stop - start) / steps
            if row.get('current', 0) >= stop - step_size:
                break

            t = time.time()
            # This will fail due to lag of triggering at the very last row
            v_total = self.dmm.next_reading()
            data = {'v_total': v_total}
            self.add_to_current_measurement(data)
            print('Read DMM: {}'.format(time.time() - t))

            # if (i > 15) and (len(data) < 5):
            if (i > 15) and (row is None):
                err_count += 1
                print('err_count: ', err_count)

            if err_count > 2:
                break

            if i % 5 == 0:
                print('read cryostat')
                self._read_cryostat()

        print('End measurement')
        # nvz = self.scpi_comm('SOUR:DCON:NVZ?').strip()
        # print('NVZero', nvz)
        self.current_source.end_delta_measurement()
        time.sleep(2)

        # Indicate that the measurement is completed
        self.reset_current_measurement(None)

    def test(self):
        # self.instrument_id()
        self.differential_conductance_measurement(
            comment='Test run',
            start=-1e-5,
            stop=1e-5,
            step=1e-7,
            delta=1.1e-7
        )


if __name__ == '__main__':
    cdc = CryostatDifferentialConductance()
    cdc.test()
