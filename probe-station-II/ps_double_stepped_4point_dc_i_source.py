import time
import numpy as np
from ps_dc_base import ProbeStationDCBase


class ProbeStation4PointDoubleSteppedISource(ProbeStationDCBase):
    def __init__(self):
        # super().__init__(self=self)
        super().__init__()
        self.aborted = False
        time.sleep(0.2)

    def abort_measurement(self):
        print('ABORT')
        self.source.set_current(0)
        self.aborted = True
        self.reset_current_measurement('aborting', error='Aborted', keep_measuring=True)

    def _setup_data_log(self, comment, source, gate):
        labels = {'v_total': 'Vtotal'}
        self._add_metadata(labels, 302, comment)

        labels = {'v_backgate': 'Gate voltage'}
        self._add_metadata(labels, 302, comment, nplc=gate['nplc'])
        labels = {'i_backgate': 'Gate current'}
        self._add_metadata(labels, 302, comment, nplc=gate['nplc'], limit=gate['limit'])

        labels = {'v_xx': 'Vxx'}
        self._add_metadata(labels, 302, comment, nplc=source['nplc'])
        labels = {'current': 'Current'}
        self._add_metadata(
            labels, 302, comment, nplc=source['nplc'], limit=source['limit']
        )
        self.reset_current_measurement('4PointDoubleStepped')

    def _configure_instruments(self, source, gate):
        # Configure instruments:
        print('Configure Back gate')
        gate_range = max(abs(gate['start']), abs(gate['stop']))
        self._configure_back_gate(
            source_range=gate_range, limit=gate['limit'], nplc=source['nplc']
        )

        source_range = max(abs(source['start']), abs(source['stop']))
        print('Configure DMM')
        self._configure_dmm(v_limit=source_range)

        print('Configure Source')
        self._configure_source(
            function='i',
            source_range=source_range,
            limit=source['limit'],
            nplc=source['nplc'],
            remote_sense=True,
        )
        print('Configure done')

    def _ramp_gate(self, v_from, v_to, rate=0.5, force_even_if_abort=False):
        # Rate is the allowed gate-sweep rate in V/s
        # todo: strongly consider to move this up to dc_base
        sign = np.sign(v_to - v_from)
        step_size = 0.025

        ramp_list = list(np.arange(v_from, v_to, step_size * sign)) + [v_to]
        for gate_ramp_v in ramp_list:
            if (self.current_measurement['type'] == 'aborting') and (
                not force_even_if_abort
            ):
                print('Measurement aborted - stop gate ramp')
                break
            print('Ramping gate to {}'.format(gate_ramp_v))
            self.back_gate.set_voltage(gate_ramp_v)
            self.read_gate()
            self.read_source(function='i')
            time.sleep(step_size / rate)

    def dc_4_point_measurement_i_source(
        self, comment, inner: str, source: dict, gate: dict, **kwargs
    ):
        """
        Perform a 4-point DC vi-measurement.
        :param start: The lowest voltage in the sweep
        :param stop: The highest voltage in the sweep
        :param steps: Number of steps in sweep
        :param nplc: Integration time of  measurements
        :params gate_v: Optional gate voltage at which the sweep is performed
        :v_limit: Maximal allowed voltage, default is 1.0
        """
        self._setup_data_log(comment=comment, source=source, gate=gate)
        self._configure_instruments(source=source, gate=gate)

        # Calculate the sweeps
        gate_steps = self._calculate_steps(**gate)
        source_steps = self._calculate_steps(**source)

        assert inner.lower() in ('source', 'gate')
        if inner.lower() == 'source':
            inner_steps = source_steps
            outer_steps = gate_steps
            inner_inst = self.source
            outer_inst = self.back_gate
            # TODO: override set_voltage into ramp, should be implented
            # at the point where the instruments are assigned (in measurement_base)
        else:
            inner_steps = gate_steps
            outer_steps = source_steps
            inner_inst = self.back_gate
            outer_inst = self.source

        print('Inner steps are: ', inner_steps)
        print('Outer steps are: ', outer_steps)

        # Ramp to the first gate voltage:
        self._ramp_gate(v_from=0, v_to=gate['start'])

        for outer_v in outer_steps:
            if self.current_measurement['type'] == 'aborting':
                continue
            outer_inst.set_voltage(outer_v)
            print('Set outer to: {}'.format(outer_v))

            for inner_i in inner_steps:
                if self.current_measurement['type'] == 'aborting':
                    # Measurement has been aborted, skip through the
                    # rest of the steps
                    continue
                inner_inst.set_current(inner_i)
                print('Set inner to {}'.format(inner_i))
                time.sleep(0.05)
                if not self._check_I_source_status():
                    # TODO!!! This always returns True!!!!
                    return

                self.read_source(function='i')  # Also reads 2-point via the DMM
                self.read_gate()

        time.sleep(2)

        if not self.aborted:
            # Ramp gate back to zero
            self._ramp_gate(v_from=gate['stop'], v_to=0)
            self.reset_current_measurement(None)
        else:
            print('Ramp gate back to zero')
            self.back_gate.trigger_measurement('gate_data')
            reading = self.back_gate.read_latest('gate_data')
            v_from = reading['source_value']
            self._ramp_gate(v_from=v_from, v_to=0, force_even_if_abort=True)
            self.reset_current_measurement(None, error='Aborted')

        # Indicate that the measurement is completed
        self.aborted = False
        self.back_gate.output_state(False)
        self.source.output_state(False)
        self.reset_current_measurement(None)

    def test(self):
        # self.instrument_id()
        self.dc_4_point_measurement_i_source(
            comment='test() - double stepped',
            inner='source',  # outer will be gate
            # inner='gate',  # ourter will be source
            source={
                'start': -2e-4,
                'stop': 2e-3,
                'steps': 50,
                'limit': 10,
                'nplc': 1,
            },
            gate={
                'start': -5.0,
                'stop': 5.0,
                'steps': 3,
                'limit': 1e-7,
                'nplc': 1,
            },
        )


if __name__ == '__main__':
    ps = ProbeStation4PointDoubleSteppedISource()
    ps.test()
