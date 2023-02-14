import time
import numpy as np
# import logging
import threading

from linkam_measurement_base import LinkamMeasurementBase


class LinkamOneShotVanDerPauw(LinkamMeasurementBase):
    def __init__(self):
        super().__init__()
        # self.source_logger_1.set_range(10)
        # self.source_logger_2.set_range(10)

    def _calculate_steps(self, v_low, v_high, steps, repeats):
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

    def _gate_sweep(self, steps, time_pr_step, end_wait, compliance):
        """
        Perform a gate-sweep.
        """
        self.back_gate.set_source_function('v')
        self.back_gate.set_current_limit(compliance)
        self.back_gate.set_voltage(0)
        self.back_gate.output_state(True)
        time.sleep(1)
        t_step_start = time.time()

        current_1 = self.source_logger_1.read_ac_voltage() / 1e6
        current_2 = self.source_logger_2.read_ac_voltage() / 1e6
        data = {'current_1': current_1, 'current_2': current_2}
        self.add_to_current_measurement(data)

        for step in steps:
            # print('Step loop was', time.time() - t_step_start, step)
            t_step_start = time.time()
            self.back_gate.set_voltage(step)  # ~5ms
            self._read_gate()  # ~200ms - why so slow?

            dt = time.time() - t_step_start
            if dt < time_pr_step:
                time.sleep(time_pr_step - dt)

            v_1, theta_1, _ = self.lock_in_1.read_r_and_theta()  # ~35ms
            v_2, theta_2, _ = self.lock_in_2.read_r_and_theta()  # ~35ms

            data = {
                'lock_in_v1': v_1, 'lock_in_v2': v_2,
                'theta_1': theta_1, 'theta_2': theta_2,
            }
            self.add_to_current_measurement(data)

        current_1 = self.source_logger_1.read_ac_voltage() / 1e6
        current_2 = self.source_logger_2.read_ac_voltage() / 1e6
        data = {'current_1': current_1, 'current_2': current_2}
        self.add_to_current_measurement(data)

        t_end = time.time() + end_wait
        while time.time() < t_end:
            time.sleep(time_pr_step)
            self._read_gate()
            v_1, theta_1, _ = self.lock_in_1.read_r_and_theta()
            v_2, theta_2, _ = self.lock_in_2.read_r_and_theta()
            data = {
                'lock_in_v1': v_1, 'lock_in_v2': v_2,
                'theta_1': theta_1, 'theta_2': theta_2,
            }
            self.add_to_current_measurement(data)

        current_1 = self.source_logger_1.read_ac_voltage() / 1e6
        current_2 = self.source_logger_2.read_ac_voltage() / 1e6
        data = {'current_1': current_1, 'current_2': current_2}
        self.add_to_current_measurement(data)

    def one_shot_van_der_pauw(
            self, comment: str, v_low: float, v_high: float, compliance: float,
            total_steps: int, repeats: int, time_pr_step, end_wait: int
    ):
        """
        Perform a one-shot Van der Pauw using a gate and two LockIn amplifiers
        :param v_low: The lowest current in the sweep.
        :param v_high: The highest current in the sweep.
        :steps: Number of steps in the sweep.
        """

        _, _, freq1 = self.lock_in_1.read_r_and_theta()  # ~35ms
        _, _, freq2 = self.lock_in_2.read_r_and_theta()  # ~35ms
        labels = {
            'v_backgate': {'label': 'Gate voltage', 'timestep': time_pr_step},
            'i_backgate': 'Gate current',
            'theta_1': 'Theta 1',
            'theta_2': 'Theta 2',
            'current_1': 'Current 1',
            'current_2': 'Current 2',
            'lock_in_v1': {'label': 'LockIn 1', 'frequency': freq1},
            'lock_in_v2': {'label': 'LockIn 2', 'frequency': freq2}
        }
        self._add_metadata(labels, meas_type=204, comment=comment)
        self.reset_current_measurement('one_shot_van_der_pauw')

        # self.dmm.read_ac_voltage()  # Configure DMM for AC measurement
        # self._init_ac(start, stop)  # Configure current source
        # time.sleep(3)

        steps = self._calculate_steps(v_low, v_high, total_steps, repeats)
        t = threading.Thread(target=self._gate_sweep,
                             args=(steps, time_pr_step, end_wait, compliance))
        t.start()
        while t.is_alive():
            # current_1 = self.source_logger_1.read_ac_voltage() / 1e6
            # current_2 = self.source_logger_2.read_ac_voltage() / 1e6
            # data = {
            #    'current_1': current_1, 'current_2': current_2

            # }
            # self.add_to_current_measurement(data)
            if self.current_measurement['type'] is None:
                # Measurement has been aborted, skip through the
                # rest of the steps
                t.stop()

            print('waiting')
            time.sleep(5)
        # TODO!! Handle the case of non-succes!
        # if self.current_measurement['error']:

        # # Indicate that the measurment is completed
        # self.current_source.stop_and_unarm()
        self.reset_current_measurement(None)

    def test(self):
        # self.instrument_id()
        # self.set_lock_in_frequency(12523.2)
        self.one_shot_van_der_pauw(
            v_low=-3.0,
            v_high=3.0,
            total_steps=51,
            repeats=5,
            time_pr_step=0.1,
            end_wait=10
        )


if __name__ == '__main__':
    Test = LinkamOneShotVanDerPauw()
    Test.test()
