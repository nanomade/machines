import time

from cryostat_dc_base import CryostatDCBase


class Cryostat4PointHomeBrewDelta(CryostatDCBase):
    def __init__(self):
        trigger_list = [
            1,  # Vxy - white
            2,  # DMM - brown
            3,  # Vxx - Green
            4,  # Osciloscope - Yellow
        ]
        super().__init__(trigger_list)

    def abort_measurement(self):
        print('ABORT')
        self.reset_current_measurement(None, error='Aborted')

    def home_brew_delta_4_point_measurement(
            self, comment, start: float, stop: float, steps: int,
            repeats: int = 1, v_limit: float = 1.0, nplc: float = 1,
            back_gate_v: float = None, front_gate_v = None, **kwargs
    ):
        # """
        # Perform a 4-point DC iv-measurement.
        # :param start: The lowest current in the sweep
        # :param stop: The highest current in the sweep
        # :param steps: Number of steps in sweep
        # :param nplc: Integration time of voltage measurements
        # :params gate_v: Optional gate voltage at which the sweep is performed
        # :v_limit: Maximal allowed voltage, default is 1.0
        # """
        # labels = {
        #     'v_total': 'Vtotal', 'current': 'Current', 'b_field': 'B-Field',
        #     'vti_temp': 'VTI Temperature', 'sample_temp': 'Sample temperature'
        # }
        # self._add_metadata(labels, 201, comment)

        # if back_gate_v is not None:
        #     labels = {
        #         'v_backgate': 'Back Gate voltage', 'i_backgate': 'Back Gate current',
        #     }
        #     self._add_metadata(labels, 201, comment)
        self.configure_back_gate()
        #     self.back_gate.set_voltage(back_gate_v)
            
        # if front_gate_v is not None:
        #     labels = {
        #         'v_frontgate': 'Front Gate voltage', 'i_frontgate': 'Front Gate current',
        #     }
        #     self._add_metadata(labels, 201, comment)
        #     self.configure_front_gate()
        #     self.front_gate.set_voltage(back_gate_v)
        
        # labels = {'v_xx': 'Vxx', 'v_xy': 'Vxy'}
        # self._add_metadata(labels, 201, comment, nplc=nplc)
        # self.reset_current_measurement('dc_sweep')

        # self._configure_dmm(v_limit)
        # self._configure_source(v_limit=v_limit, current_range=stop)
        self._configure_source(v_limit=v_limit, current_range=1e-6)
        self._configure_nano_voltmeters(nplc)

        self.current_source.output_state(True)
        current = 1e-8
        print()
        print()

        #for i in range(0, 50):
        while True:
            # time.sleep(1)
            self.current_source.set_current(current)
            time.sleep(0.01)
            self.back_gate.trigger_measurement()
            data_high = self._read_voltages(10)

            # time.sleep(1)
            self.current_source.set_current(current * -1)
            time.sleep(0.01)
            self.back_gate.trigger_measurement()
            data_low = self._read_voltages(50)
            # print(data_high, data_low)
            v_xx = (data_high['v_xx'] - data_low['v_xx']) / 2
            v_xy = (data_high['v_xy'] - data_low['v_xy']) / 2
            v_total = (data_high['v_total'] - data_low['v_total']) / 2

            # msg = 'Vtotal_high: {:.1f}mV. Vtotal_low: {:.1f}mV.  Vxx: {:.1f}mV. Vxy: {:.1f}mV. Vtotal: {:.1f}mV'
            # print(msg.format(data_high['v_total'] * 1000, data_low['v_total'] * 1000, v_xx * 1000, v_xy * 1000, v_total * 1000))
            msg = 'Vxx: {:.1f}mV. Vxy: {:.1f}mV. Vtotal: {:.1f}mV'
            print(msg.format(v_xx * 1000, v_xy * 1000, v_total * 1000))
        # time.sleep(2)
        # self.current_source.set_current(start)
        # time.sleep(1)

        # # # Activate a few triggers to ensure measurement gets started
        # # for _ in range(0, 3):
        # #    self._read_voltages(nplc, store_gate=False)

        # iteration = 0
        # for current in self._calculate_steps(start, stop, steps, repeats):
        #     iteration += 1
        #     if self.current_measurement['type'] is None:
        #         # Measurement has been aborted, skip through the
        #         # rest of the steps
        #         continue

        #     self.current_source.set_current(current)
        #     time.sleep(0.05)
        #     if not self._check_I_source_status():
        #         return

        #     if iteration % 5 == 0:
        #         read = False
        #         if self.front_gate is not None:
        #             self.front_gate.trigger_measurement()
        #         if self.back_gate is not None:
        #             self.back_gate.trigger_measurement()
        #             self.read_gate()
        #     else:
        #         self.back_gate.trigger_measurement()

        #     data = self._read_voltages(nplc)
        #     data['current'] = current
        #     print('Data: ', data)
        #     self.add_to_current_measurement(data)
        #     self._read_cryostat()

        # time.sleep(2)
        # # Indicate that the measurement is completed
        # self.current_source.output_state(False)
        # self.reset_current_measurement(None)

    def test(self):
        # self.instrument_id()
        self.home_brew_delta_4_point_measurement(
            comment='Internal test',
            start=-5e-9,
            stop=5e-9,
            steps=101,
            repeats=1,
            v_limit=5,
            back_gate_v=1,
            front_gate_v=-1,
        )


if __name__ == '__main__':
    hbd = Cryostat4PointHomeBrewDelta()
    hbd.test()
