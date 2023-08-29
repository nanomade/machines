import time
import threading

# from cryostat_measurement_base import CryostatMeasurementBase
from cryostat_dc_base import CryostatDCBase


class Cryostat4PointDC(CryostatDCBase):
    def __init__(self):
        super().__init__()

    def abort_measurement(self):
        print('ABORT')
        self.reset_current_measurement(None, error='Aborted')

    def dc_4_point_measurement(self, comment, start: float, stop: float, steps: int, v_limit=1.0, **kwargs):
        """
        Perform a 4-point DC iv-measurement.
        :param start: The lowest current in the sweep.
        :param stop: The highest current in the sweep.
        :steps: Number of steps in the sweep.
        :v_limit: Maximal allowed voltage, default is 1.0
        """
        labels = {'v_total': 'Vtotal', 'v_xx': 'Vxx', 'v_xy': 'Vxy', 'current': 'Current',
                  'b_field': 'B-Field', 'vti_temp': 'VTI Temperature', 'sample_temp': 'Sample temperature'}
        self._add_metadata(labels, 201, comment, timestep=0.2)
        self.reset_current_measurement('dc_sweep')

        # Configure instruments:
        self._configure_back_gate()  # Misused to trigger 2182a's
        self._configure_dmm(v_limit)
        self._configure_source(v_limit=v_limit, current_range=stop)
        self._configure_nano_voltmeters(5)  # todo: Configurable nplc

        time.sleep(1)
        self.current_source.set_current(start)

        for current in self._calculate_steps(start, stop, steps):
            if self.current_measurement['type'] is None:
                # Measurement has been aborted, skip through the
                # rest of the steps
                continue

            self.current_source.set_current(current)
            time.sleep(0.05)
            if not self._check_I_source_status():
                return

            data = self._read_voltages(5, store_gate=False)
            # # t = threading.Thread(target=self._ac_4_point_sweep,
            # #                      args=(current_steps,))
            # t_vxx = threading.Thread(target=self.masure_voltage_xx.start_measurement)
            # t_vxx.start()
            # t_vtotal = threading.Thread(target=self.masure_voltage_total.start_measurement)
            # t_vtotal.start()

            # t = time.time()
            # v_xx = self.masure_voltage_xx.read_voltage()
            # v_total = self.masure_voltage_total.read_voltage()
            # print('Measure time: {}'.format(time.time() - t))
            data['current'] = current
            # data = {'current': current, 'v_total': v_total, 'v_xx': v_xx}
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
