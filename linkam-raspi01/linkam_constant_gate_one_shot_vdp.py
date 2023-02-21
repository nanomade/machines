import time
import numpy as np
# import logging
import threading

from linkam_measurement_base import LinkamMeasurementBase


class LinkamConstantGateVDP(LinkamMeasurementBase):
    def __init__(self):
        super().__init__()
        self.allow_abort = True
        # self.source_logger_1.set_range(10)
        # self.source_logger_2.set_range(10)

    def _constant_gate_measure(
            self,
            gate_voltage: float,
            steps: int,
            time_pr_step: float,
            meas_time: float,
            end_wait: float,
            compliance: float
    ):
        """
        Perform a constant gate-voltate measurement
        """
        self._prepare_gate(compliance)
        self._read_current_sources()

        step_size = gate_voltage / (steps - 1)
        up = list(np.arange(0, gate_voltage, step_size)) + [gate_voltage]
        down = list(np.arange(gate_voltage, 0, -1 * step_size)) + [0]

        up_completed = self._step_measure(up, time_pr_step)

        t_end = time.time() + meas_time
        while time.time() < t_end and not self.aborted:
            time.sleep(time_pr_step)
            self._read_gate()
            v_1, theta_1, _ = self.lock_in_1.read_r_and_theta()
            v_2, theta_2, _ = self.lock_in_2.read_r_and_theta()
            data = {
                'lock_in_v1': v_1, 'lock_in_v2': v_2,
                'theta_1': theta_1, 'theta_2': theta_2,
            }
            self.add_to_current_measurement(data)
            self._read_current_sources()

        # Independent of if the measurement was aborted or not, we now
        # need to have access to self._step_measure()
        self.aborted = False

        if not up_completed:
            # Up was never completed, we should go down from the actual current gate
            actual_gate_v = self.back_gate.read_voltage()
            down = list(np.arange(actual_gate_v, 0,
                                  -0.1 * np.sign(actual_gate_v))) + [0]

        self.allow_abort = False  # We cannot abort the step down
        self._step_measure(down, time_pr_step)
        self.allow_abort = True

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
        self._read_current_sources()

    def abort_measurement(self):
        if self.allow_abort:
            self.aborted = True

    def constant_gate_one_shot_vdp(
            self, comment: str, gate_voltage: float, compliance: float,
            steps: int, time_pr_step, meas_time: float, end_wait: float,
            **kwargs
    ):
        """
        Perform a constant gated one-shot Van der Pauw using a gate and two
        LockIn amplifiers
        :param gate_voltage: The voltage to keep the gate at
        :steps: Number of steps to reach the hold voltage.
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
        # 205: Constant gate van der pauw
        self._add_metadata(labels, meas_type=205, comment=comment)
        self.reset_current_measurement('constant_gate_one_shot_vdp')

        t = threading.Thread(
            target=self._constant_gate_measure,
            args=(gate_voltage, steps, time_pr_step, meas_time, end_wait, compliance)
        )
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

        self.reset_current_measurement(None)

    def test(self):
        self.constant_gate_one_shot_vdp(
            comment='Python test function',
            gate_voltage=5,
            compliance=1e-5,
            steps=20,
            time_pr_step=1,
            meas_time=60.0,
            end_wait=20,
        )


if __name__ == '__main__':
    Test = LinkamConstantGateVDP()
    Test.test()
