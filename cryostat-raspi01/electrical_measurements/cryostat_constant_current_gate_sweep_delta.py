# TODO: THIS SHOULD BE MERGED WITH NON-DELTA GATE SWEEP!
# the to programs essentially does the same thing except for
# the configuration of the Delta/non-delta mode

import time

import numpy as np

# from PyExpLabSys.drivers.keithley_2182 import Keithley2182
from cryostat_measurement_base import CryostatMeasurementBase
from cryostat_dc_base import CryostatDCBase


class CryostatDeltaConstantCurrentGateSweep(CryostatDCBase):
    def __init__(self):
        trigger_list = [
            2,  # DMM - brown
            4,  # Osciloscope - Yellow
        ]
        super().__init__()

    def abort_measurement(self):
        print('ABORT')
        self.reset_current_measurement(None, error='Aborted')

    def delta_constant_current_gate_sweep(
            self, comment: str, current: float, v_low: float, v_high: float,
            steps: int, repeats: int, v_limit: int = 1, v_xx_range: float = 0.1,
            nplc: int = 5,
            **kwargs
    ):
        """
        TODO!
        """
        labels = {
            'v_backgate': 'Gate voltage', 'i_backgate': 'Gate current',
            'b_field': 'B-Field', 'vti_temp': 'VTI Temperature',
            'sample_temp': 'Sample temperature'
        }
        # 209 is now delta gate sweep!!!!!
        self._add_metadata(labels, 209, comment)
        # TODO: Add v_limit as metadata
        labels = {'v_total': 'Vtotal'}
        self._add_metadata(labels, 209, comment, current=current)
        # labels = {'v_xx': 'Vxx', 'v_xy': 'Vxy'}
        labels = {'v_xx': 'Vxx'}
        self._add_metadata(labels, 209, comment, current=current, nplc=nplc)
        self.reset_current_measurement('delta_gate_sweep')

        # Configure instruments:
        self._configure_source(v_limit=v_limit, current_range=current)
        self._configure_dmm(v_limit=v_limit)

        # TODO! There is a speed-up trick by disabling front-end zero - look into this!
        self._configure_nano_voltmeters(nplc)

        
        self._configure_back_gate()
        # time.sleep(1)
        # I do not know, why this is necessary - find out!!!
        # self.back_gate.set_current_limit(1e-6)

        # Set the constant current level
        self.current_source.set_current(current)
        time.sleep(0.1)
        if not self._check_I_source_status():
            return

        time.sleep(0.1)
        self.read_gate()

        self.current_source.prepare_delta_measurement(current, v_xx_range)
        time.sleep(3.0)

        aborted = False
        gate_softland_from = None
        for gate_v in self._calculate_steps(v_low, v_high, steps, repeats):
            if self.current_measurement['type'] is None:
                # Measurement has been aborted, skip through the
                # rest of the steps
                if not aborted:
                    gate_softland_from = gate_v
                aborted = True
                continue

            print('Set back gate', gate_v)
            self.back_gate.set_voltage(gate_v)
            # Source measure dealy:
            time.sleep(0.001)  # TODO: Make the delay configurable
        
            self._read_cryostat()
            time.sleep(1.0)
            try:
                v_xx, meas_time = self.current_source.read_delta_measurement()
            except ValueError:
                print('Value error, not enough elements')
                continue

            # v_xx = abs(v_xx)  # Not really sure how this can be negative...

            # This is measured at a random time in the delta interval and thus
            # has a random sign.
            # todo: Keep track of measurements and do delta here as well
            v_total = abs(self.dmm.next_reading())

            data = {'v_xx': v_xx, 'v_total': v_total}
            self.add_to_current_measurement(data)
            # Todo: Speed can be gained by running this in a thread:
            self.read_gate()

        print('Stopping from:', gate_softland_from)
        if gate_softland_from is not None:
            if gate_softland_from > 0:
                steps = np.arange(gate_softland_from, -0.05, -0.05)
            else:
                steps = np.arange(gate_softland_from, 0.05, 0.05)
                
            for stopping_gate_v in steps:
                print('Ramp gate to 0: ', stopping_gate_v)
                time.sleep(0.2)
                self.back_gate.set_voltage(stopping_gate_v)

        # Indicate that the measurement is completed
        self.current_source.end_delta_measurement()

        time.sleep(5)
        self.reset_current_measurement(None)

    def test(self):
        self.delta_constant_current_gate_sweep(
            'test run', current = 4e-9, v_low=-3, v_high=1,
            steps=101, repeats=1, v_limit=2, v_xx_range=1, nplc=5,
        )


if __name__ == '__main__':
    cdccgs = CryostatDeltaConstantCurrentGateSweep()
    cdccgs.test()
