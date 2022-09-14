import time
# import logging
import threading

from PyExpLabSys.drivers.keithley_2400 import Keithley2400

from cryostat_ac_base import CryostatACBase


class CryostatGated4PointAC(CryostatACBase):
    def __init__(self):
        super().__init__()
        self.back_gate = Keithley2400(interface='gpib', gpib_address=22)

    def gated_ac_4_point_measurement(
            self,
            i_start: float, i_stop: float, total_i_steps: int,
            backgate_from, backgate_to, gate_steps
    ):
        """
        Perform a gated 4-point AC iv-measurement.
        :param i_start: The lowest current in the sweep.
        :param i_stop: The highest current in the sweep.
        :param total_i_steps: Number of steps in the sweep.
        :param backgate_from:
        :param backgate_to:
        :param gate_steps:
        """
        labels = {
            'v_total': 'Vtotal', 'v_sample': 'Vsample',
            'current': 'Current', 'theta': 'Theta',
            'v_backgate': 'Back Gate Voltage', 'i_backgate': 'Back Gate Leak'
        }
        self._add_metadata(labels, 203, 'Gated AC measurement',
                           freq=self.lock_in_frequency)

        self.reset_current_measurement('gated_ac_sweep')

        # Todo: Set correct ranges for compliance and source
        self.back_gate.set_source_function('v')
        self.back_gate.set_current_limit(1e-4)
        self.back_gate.set_voltage(backgate_from)
        self.back_gate.output_state(True)
        time.sleep(0.1)
        self._read_gate()

        gate_steps = self._calculate_steps(backgate_from, backgate_to, gate_steps)

        self._init_ac(i_start, i_stop)  # Configure current source
        current_steps = self._calculate_steps(i_start, i_stop, total_i_steps)

        for gate_v in gate_steps:
            if self.current_measurement['type'] is None:
                continue
            self.back_gate.set_voltage(gate_v)
            time.sleep(0.5)
            self._read_gate()

            t = threading.Thread(target=self._ac_4_point_sweep,
                                 args=(current_steps,))
            t.start()
            while t.is_alive():
                if self.current_measurement['type'] is None:
                    # Measurement has been aborted
                    t.stop()

                # Backgate can be measured slower than the inner sweep,
                # we do it periodically while waiting for the sweep
                print('waiting')
                time.sleep(1)
                self._read_gate()
            self._read_gate()

        # TODO!! Handle the case of non-succes!
        # if self.current_measurement['error']:

        # Indicate that the measurment is completed
        self.current_source.stop_and_unarm()
        self.back_gate.set_voltage(0)
        self.back_gate.output_state(False)
        self.reset_current_measurement(None)

    def test(self):
        # self.instrument_id()
        self.gated_ac_4_point_measurement(
            i_start=1e-7,
            i_stop=5e-6,
            total_i_steps=50,
            backgate_from=-0.01,
            backgate_to=0.01,
            gate_steps=5
        )


if __name__ == '__main__':
    cm = CryostatGated4PointAC()
    cm.test()
