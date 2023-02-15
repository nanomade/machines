import time
import numpy as np
# import logging
import threading

from linkam_measurement_base import LinkamMeasurementBase


class LinkamSweepedOneShotVDP(LinkamMeasurementBase):
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
        self._prepare_gate(compliance)
        self._read_current_sources()
        completed = self._step_measure(steps, time_pr_step)

        if not completed:  # Measurement has been aborted
            # Cancel global abort, we need to get the step-functionality back
            self.aborted = False
            gate_v = self.back_gate.read_voltage()
            steps = np.arange(gate_v, 0, -0.1 * np.sign(gate_v))
            self._step_measure(steps, 0.2)

        # zig-zag step is done, now perform end_wait
        self._read_current_sources()
        t_end = time.time() + end_wait
        while time.time() < t_end:
            time.sleep(time_pr_step)
            self._read_gate()
            self._read_lock_ins()
        self._read_current_sources()

    def abort_measurement(self):
        self.aborted = True

    def one_shot_van_der_pauw(
            self, comment: str, v_low: float, v_high: float, compliance: float,
            total_steps: int, repeats: int, time_pr_step, end_wait: int, **kwargs
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

        steps = self._calculate_steps(v_low, v_high, total_steps, repeats)
        t = threading.Thread(target=self._gate_sweep,
                             args=(steps, time_pr_step, end_wait, compliance))
        t.start()
        while t.is_alive():
            if self.current_measurement['type'] is None:
                # Measurement has been aborted, skip through the rest of the steps
                t.stop()
            print('waiting')
            time.sleep(2)

        self.reset_current_measurement(None)

    def test(self):
        self.one_shot_van_der_pauw(
            comment='Test from python code',
            v_low=-3.0,
            v_high=3.0,
            total_steps=51,
            repeats=5,
            time_pr_step=0.1,
            end_wait=10,
            compliance=1e-4,
        )


if __name__ == '__main__':
    Test = LinkamSweepedOneShotVDP()
    Test.test()
