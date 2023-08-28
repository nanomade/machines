import time
import threading

import numpy as np

from PyExpLabSys.drivers.keithley_2400 import Keithley2400
from PyExpLabSys.drivers.keithley_2182 import Keithley2182
from cryostat_measurement_base import CryostatMeasurementBase

from cryostat_threaded_voltage import MeasureVxx
from cryostat_threaded_voltage import MeasureVxy
from cryostat_threaded_voltage import MeasureVTotal


class CryostatConstantCurrentGateSweep(CryostatMeasurementBase):
    def __init__(self):
        super().__init__()

        self.back_gate = Keithley2400(interface='gpib', gpib_address=22)
        # self.dmm and self.current_source are always in the base
        # xy_nanov is interfaced via the current source
        device = 'usb-Prolific_Technology_Inc._USB-Serial_Controller_D-if00-port0'
        self.xy_nanov = Keithley2182(
            interface='serial',
            device='/dev/serial/by-id/' + device,
        )
        self.masure_voltage_xx = MeasureVxx(self.current_source)
        self.masure_voltage_xy = MeasureVxy(self.xy_nanov)
        self.masure_voltage_total = MeasureVTotal(self.dmm)

    def _calculate_steps(self, v_low, v_high, steps, repeats):
        """ This code is also used in the Linkham code """
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

    def abort_measurement(self):
        print('ABORT')
        self.reset_current_measurement(None, error='Aborted')

    def constant_current_gate_sweep(
            self, comment, current: float, v_low: float, v_high: float,
            steps: int, repeats: int, v_limit=1, **kwargs
    ):
        """
        Perform a gate sweep while holding a fixed current. Measure voltage.
        TODO!!!
        """
        labels = {
            'v_total': 'Vtotal', 'v_xx': 'Vxx', 'v_xy': 'Vxy',
            'v_backgate': 'Gate voltage', 'i_backgate': 'Gate current',
            'b_field': 'B-Field', 'vti_temp': 'VTI Temperature',
            'sample_temp': 'Sample temperature'
        }
        self._add_metadata(labels, 208, comment, current=current, timestep=0.2)
        self.reset_current_measurement('dc_gate_sweep')

        # Configure instruments:
        # Current source
        self.current_source.set_voltage_limit(v_limit)
        self.current_source.set_current_range(current)
        self.current_source.set_current(0)
        self.current_source.output_state(True)

        # Model 2000 2-point measurement
        self.dmm.configure_measurement_type('volt:dc')
        self.dmm.set_range(v_limit)
        self.dmm.set_integration_time(2)
        self.dmm.scpi_comm(':INIT:CONT ON')  # TODO: Add this to driver

        self.current_source._2182a_comm(':SENSE:VOLT:CHANNEL1:RANGE:AUTO ON')
        self.xy_nanov.set_range(0, 0)
        self.current_source._2182a_comm('SENSE:VOLTAGE:NPLCYCLES 5')
        self.xy_nanov.set_integration_time(5)
        self.current_source._2182a_comm()

        # Set the constant current level
        self.current_source.set_current(current)
        time.sleep(0.1)
        if not self._check_I_source_status():
            return

        self.back_gate.set_source_function('v')
        self.back_gate.set_current_limit(1e-4)
        self.back_gate.set_voltage(0)
        self.back_gate.output_state(True)

        time.sleep(0.1)
        self._read_gate()

        aborted = False
        for gate_v in self._calculate_steps(v_low, v_high, steps, repeats):
            if self.current_measurement['type'] is None:
                # Measurement has been aborted, skip through the
                # rest of the steps
                aborted = True
                continue

            self.back_gate.set_voltage(gate_v)
            t_vxx = threading.Thread(
                target=self.masure_voltage_xx.start_measurement
            )
            t_vxx.start()
            t_vxy = threading.Thread(
                target=self.masure_voltage_xy.start_measurement
            )
            t_vxy.start()
            t_vtotal = threading.Thread(
                target=self.masure_voltage_total.start_measurement
            )
            t_vtotal.start()
            # This will both read the gate and trigger the 2182a's
            self._read_gate()
            v_xx = self.masure_voltage_xx.read_voltage()
            v_xy = self.masure_voltage_xy.read_voltage()
            print(v_xx, v_xy)
            v_total = self.masure_voltage_total.read_voltage()

            data = {'v_total': v_total, 'v_xx': v_xx, 'v_xy': v_xy}
            if v_xx < -1000:
                del(data['v_xx'])
            if v_xy < -1000:
                del(data['v_xy'])

            self.add_to_current_measurement(data)
            self._read_cryostat()

        if aborted:
            gate_v = self.back_gate.read_voltage()
            steps = np.arange(gate_v, 0, -0.2 * np.sign(gate_v))
            for gate_v in steps:
                self.back_gate.set_voltage(gate_v)
                time.sleep(0.25)

                t_vxx = threading.Thread(
                    target=self.masure_voltage_xx.start_measurement
                )
                t_vxx.start()
                t_vxy = threading.Thread(
                    target=self.masure_voltage_xy.start_measurement
                )
                t_vxy.start()
                t_vtotal = threading.Thread(
                    target=self.masure_voltage_total.start_measurement
                )
                t_vtotal.start()
                self._read_gate()
                v_xx = self.masure_voltage_xx.read_voltage()
                v_xy = self.masure_voltage_xy.read_voltage()
                v_total = self.masure_voltage_total.read_voltage()
                data = {'v_xx': v_xx, 'v_xy': v_xy, 'v_total': v_total}
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
