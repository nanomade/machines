# import time
import threading
# import logging

import numpy as np

from PyExpLabSys.drivers.keithley_2182 import Keithley2182

from cryostat_measurement_base import CryostatMeasurementBase
from cryostat_threaded_voltage import MeasureVxx
from cryostat_threaded_voltage import MeasureVxy
from cryostat_threaded_voltage import MeasureVTotal


class CryostatDCBase(CryostatMeasurementBase):
    def __init__(self):
        super().__init__()

        # self.dmm and self.current_source are always in the base
        # xx_nanov is interfaced via the current source for delta and
        # differential conductance, and via the rs232 port for DC
        # measurements (which is the relevant part here).

        device = 'usb-1a86_USB2.0-Ser_-if00-port0'
        self.xx_nanov = Keithley2182(
            interface='serial',
            device='/dev/serial/by-id/' + device,
        )

        device = 'usb-Prolific_Technology_Inc._USB-Serial_Controller_D-if00-port0'
        self.xy_nanov = Keithley2182(
            interface='serial',
            device='/dev/serial/by-id/' + device,
        )
        self.masure_voltage_xx = MeasureVxx(self.xx_nanov)
        self.masure_voltage_xy = MeasureVxy(self.xy_nanov)
        self.masure_voltage_total = MeasureVTotal(self.dmm)

    # This code is also used in the Linkham code
    def _calculate_steps(self, v_low, v_high, steps, repeats):
        """
        Calculate a set gate steps.
        Consider to move to CryostatMeasurementBase
        """
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

    def _configure_dmm(self, v_limit):
        """
        Configure  Model 2000 used for 2-point measurement
        The unit is set up to measure on the buffered guard output of
        the 6221.
        """
        self.dmm.configure_measurement_type('volt:dc')
        self.dmm.set_range(v_limit)
        self.dmm.set_integration_time(2)
        self.dmm.set_trigger_source(external=True)
        # TODO: Replace the line below with a line that configures a trigger
        self.dmm.instr.write(':INIT:CONT ON')  # TODO: Add this to driver

    def _configure_source(self, v_limit, current_range):
        """
        Configure current source
        """
        self.current_source.set_voltage_limit(v_limit)
        self.current_source.set_current_range(current_range)
        self.current_source.set_current(0)
        self.current_source.output_state(True)

    def _configure_nano_voltmeters(self, nplc):
        """
        Confgire the 2182a's for voltage measurement
        todo: accept other range than auto-range
        """
        self.xx_nanov.set_range(0, 0)
        self.xy_nanov.set_range(0, 0)
        self.xx_nanov.set_integration_time(nplc)
        self.xy_nanov.set_integration_time(nplc)
        self.xx_nanov.set_trigger_source(external=True)
        self.xy_nanov.set_trigger_source(external=True)

    def _read_voltages(self, nplc, store_gate=True):
        # Prepare to listen for triggers
        t_vxx = threading.Thread(
            target=self.masure_voltage_xx.start_measurement,
            kwargs={'nplc': nplc}
        )
        t_vxx.start()
        t_vxy = threading.Thread(
            target=self.masure_voltage_xy.start_measurement,
            kwargs={'nplc': nplc}
        )
        t_vxy.start()
        t_vtotal = threading.Thread(
            target=self.masure_voltage_total.start_measurement,
            # kwargs={'nplc': nplc}  # TODO!
        )
        t_vtotal.start()

        # This will both read the gate and trigger the 2182a's
        # TODO: It is now possible to trigger measurements independant
        # of reading the gate.
        self.read_gate(store_data=store_gate)

        # Read the measured result
        v_total = self.masure_voltage_total.read_voltage()
        v_xy = self.masure_voltage_xy.read_voltage()
        v_xx = self.masure_voltage_xx.read_voltage()
        data = {'v_total': v_total, 'v_xx': v_xx, 'v_xy': v_xy}
        if v_xx < -1000:
            print('ERROR IN Vxx!')
            del(data['v_xx'])
        if v_xy < -1000:
            print('ERROR IN Vxy!')
            del(data['v_xy'])
        return data
