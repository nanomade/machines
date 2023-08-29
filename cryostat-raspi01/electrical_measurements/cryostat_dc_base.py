# import time
import threading
# import logging

from PyExpLabSys.drivers.keithley_2400 import Keithley2400
from PyExpLabSys.drivers.keithley_2182 import Keithley2182

from cryostat_measurement_base import CryostatMeasurementBase
from cryostat_threaded_voltage import MeasureVxx
from cryostat_threaded_voltage import MeasureVxy
from cryostat_threaded_voltage import MeasureVTotal


class CryostatDCBase(CryostatMeasurementBase):
    def __init__(self):
        super().__init__()

        # Back gate is not used by all DC measurements, but currently
        # it is also being mis-used for triggering in non-gated
        # measurements. This might change in the future :)
        self.back_gate = Keithley2400(interface='gpib', gpib_address=22)
        # self.dmm and self.current_source are always in the base
        # xx_nanov is interfaced via the current source
        device = 'usb-Prolific_Technology_Inc._USB-Serial_Controller_D-if00-port0'
        self.xy_nanov = Keithley2182(
            interface='serial',
            device='/dev/serial/by-id/' + device,
        )
        self.masure_voltage_xx = MeasureVxx(self.current_source)
        self.masure_voltage_xy = MeasureVxy(self.xy_nanov)
        self.masure_voltage_total = MeasureVTotal(self.dmm)

    def _configure_dmm(self, v_limit):
        """
        Configure  Model 2000 used for 2-point measurement
        The unit is set up to measure on the buffered guard output of
        the 6221.
        """
        self.dmm.configure_measurement_type('volt:dc')
        self.dmm.set_range(v_limit)
        self.dmm.set_integration_time(2)
        # TODO: Replace the line below with a line that configures a trigger
        self.dmm.scpi_comm(':INIT:CONT ON')  # TODO: Add this to driver

    def _configure_source(self, v_limit, current_range):
        """
        Configure current source
        """
        self.current_source.set_voltage_limit(v_limit)
        self.current_source.set_current_range(current_range)
        self.current_source.set_current(0)
        self.current_source.output_state(True)

    def _read_voltages(self, nplc):
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
        self._read_gate()

        # Read the measured result
        v_xx = self.masure_voltage_xx.read_voltage()
        v_xy = self.masure_voltage_xy.read_voltage()
        v_total = self.masure_voltage_total.read_voltage()
        print(v_xx, v_xy, v_total)
        data = {'v_total': v_total, 'v_xx': v_xx, 'v_xy': v_xy}
        if v_xx < -1000:
            print('ERROR IN Vxx!')
            del(data['v_xx'])
        if v_xy < -1000:
            print('ERROR IN Vxy!')
            del(data['v_xy'])
        return data
