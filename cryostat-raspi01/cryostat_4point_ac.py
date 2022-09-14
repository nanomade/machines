import time
# import logging
import threading

from cryostat_ac_base import CryostatACBase


class Cryostat4PointAC(CryostatACBase):
    def __init__(self):
        super().__init__()

    def ac_4_point_measurement(self, start: float, stop: float, total_steps: int):
        """
        Perform a 4-point AC iv-measurement.
        :param start: The lowest current in the sweep.
        :param stop: The highest current in the sweep.
        :steps: Number of steps in the sweep.
        """
        labels = {'v_total': 'Vtotal', 'v_sample': 'Vsample',
                  'current': 'Current', 'theta': 'Theta'}
        self._add_metadata(labels, 202, 'AC measurement',
                           freq=self.lock_in_frequency)

        self.reset_current_measurement('ac_sweep')

        # self.dmm.read_ac_voltage()  # Configure DMM for AC measurement

        self._init_ac(start, stop)  # Configure current source
        time.sleep(3)

        current_steps = self._calculate_steps(start, stop, total_steps)
        t = threading.Thread(target=self._ac_4_point_sweep,
                             args=(current_steps,))
        t.start()
        while t.is_alive():
            if self.current_measurement['type'] is None:
                # Measurement has been aborted, skip through the
                # rest of the steps
                t.stop()

            print('waiting')
            time.sleep(1)
        # TODO!! Handle the case of non-succes!
        # if self.current_measurement['error']:

        # Indicate that the measurment is completed
        self.current_source.stop_and_unarm()
        self.reset_current_measurement(None)

    def test(self):
        # self.instrument_id()
        self.set_lock_in_frequency(12523.2)
        self.ac_4_point_measurement(1.0e-7, 5.0e-6, 100)


if __name__ == '__main__':
    cm = Cryostat4PointAC()
    cm.test()
