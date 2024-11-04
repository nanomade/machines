import time
import numpy as np
from ps_dc_base import ProbeStationDCBase


class ProbeStation2PointDoubleSteppedVSource(ProbeStationDCBase):
    def __init__(self):
        # super().__init__(self=self)
        super().__init__()
        self.aborted = False
        time.sleep(0.2)

    def abort_measurement(self):
        print('ABORT')
        self.source.set_voltage(0)
        self.aborted = True
        self.reset_current_measurement('aborting', error='Aborted', keep_measuring=True)

    def _setup_data_log(self, comment, source, gate):
        labels = {'v_backgate': 'Gate voltage'}
        self._add_metadata(
            labels,
            303,
            comment,
            steps=gate['steps'],
            repeats=gate['repeats'],
            nplc=gate['nplc'],
        )
        labels = {'i_backgate': 'Gate current'}
        self._add_metadata(labels, 303, comment, nplc=gate['nplc'], limit=gate['limit'])

        labels = {'v_xx': 'Vxx'}
        self._add_metadata(
            labels,
            303,
            comment,
            steps=source['steps'],
            repeats=source['repeats'],
            nplc=source['nplc'],
        )
        labels = {'current': 'Current'}
        self._add_metadata(
            labels, 303, comment, nplc=source['nplc'], limit=source['limit']
        )
        self.reset_current_measurement('2PointDoubleSteppedVSource')

    def _configure_instruments(self, source, gate):
        # Configure instruments:
        print('Configure Back gate')
        gate_range = max(abs(gate['v_low']), abs(gate['v_high']))
        self._configure_back_gate(
            source_range=gate_range, limit=gate['limit'], nplc=gate['nplc']
        )

        source_range = max(abs(source['v_high']), abs(source['v_low']))
        print('Configure Source')
        self._configure_source(
            function='v',
            source_range=source_range,
            limit=source['limit'],
            nplc=source['nplc'],
            remote_sense=False,
        )
        print('Configure done')

    def _ramp_gate(self, v_from, v_to, rate=0.5, force_even_if_abort=False):
        # Rate is the allowed gate-sweep rate in V/s
        # todo: strongly consider to move this up to dc_base
        sign = np.sign(v_to - v_from)
        if sign == 0:
            self.back_gate.set_voltage(0)
            return
        step_size = 0.025

        if abs(v_to - v_from) < 3 * step_size:
            # This is not really a ramp, this is a continous sweep that we can
            # accept to performin one go:
            msg = 'Small step, set gate directly: {:.1f}mV'
            print(msg.format(1000 * abs(v_to - v_from)))
            self.back_gate.set_voltage(v_to)
            return

        print('Ramp gate: ', v_from, v_to, step_size, sign)
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
            self.read_source(function='v', read_dmm=False)
            time.sleep(step_size / rate)

    def dc_2_point_measurement_v_source(
        self, comment, inner: str, source: dict, gate: dict, **kwargs
    ):
        """
        Perform a 2-point DC vi-measurement.
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

        # REMOVE
        # Ramp to the first gate voltage:
        # self._ramp_gate(v_from=0, v_to=gate['v_low'])

        latest_inner = 0
        for outer_v in outer_steps:
            if self.current_measurement['type'] == 'aborting':
                continue
            outer_inst.set_voltage(outer_v)
            print('Set outer to: {}'.format(outer_v))

            for inner_v in inner_steps:
                if self.current_measurement['type'] == 'aborting':
                    # Measurement has been aborted, skip through the
                    # rest of the steps
                    continue

                if inner.lower() == 'source':
                    inner_inst.set_voltage(inner_v)
                else:
                    self._ramp_gate(v_from=latest_inner, v_to=inner_v)
                    latest_inner = inner_v

                print('Set inner to {}'.format(inner_v))
                time.sleep(0.05)
                if not self._check_I_source_status():
                    # TODO!!! This always returns True!!!!
                    return

                # This is a 2-wire measurement, no need for DMM
                self.read_source(function='v', read_dmm=False)
                self.read_gate()

        time.sleep(2)

        if not self.aborted:
            # Ramp gate back to zero
            reading = self.back_gate.read_latest('gate_data')
            self._ramp_gate(v_from=reading, v_to=0)
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
        self.dc_4_point_measurement(
            comment='test() - double stepped',
            inner='source',  # outer will be gate
            # inner='gate',  # ourter will be source
            # NPLC?
            source={
                'v_low': -0.2,
                'v_high': 0.2,
                'repeats': 2,
                'steps': 50,
                'nplc': 5,
                'limit': 2e-3,
                'nplc': 1,
                'step_type': 'linear',
            },
            gate={
                'v_low': -5.0,
                'v_high': 5.0,
                'steps': 3,
                'repeats': 4,
                'nplc': 1,
                'limit': 1e-7,
                'step_type': 'linear',
            },
        )


if __name__ == '__main__':
    ps = ProbeStation4PointDC()
    ps.test()
