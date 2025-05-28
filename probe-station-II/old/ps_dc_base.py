import time
import threading

# import logging

from ps_measurement_base import ProbeStationMeasurementBase


class ProbeStationDCBase(ProbeStationMeasurementBase):
    def __init__(self):
        super().__init__()

    def _configure_dmm(self, v_limit):
        """
        Configure  Model 2000 used for 2-point measurement
        The unit is set up to measure on the buffered output of
        the 2450.
        """
        self.dmm.configure_measurement_type('volt:dc')
        self.dmm.set_range(v_limit)
        self.dmm.set_integration_time(2)
        self.dmm.scpi_comm(':INIT:CONT ON')  # TODO: Add this to driver

    def _configure_back_gate(self, source_range, limit, nplc):
        """
        Configure the 2450 for gating.
        """
        print('Reset back gate')
        self.back_gate.reset_instrument()
        self.back_gate.use_rear_terminals()

        # Ok, for new we just go with defbuffer1... I still think it
        # would be cool to make a dedicated buffer, but it can wait...
        # print('Make and clear gate_data buffer')
        # self.back_gate.make_buffer('gate_data', 10)
        self.back_gate.clear_buffer()

        print('Set back gate source volage')
        self.back_gate.set_source_function(function='v', source_range=source_range)
        # Temporarily set sense to auto to avoid temporary range conflicts
        self.back_gate.set_sense_function(function='i', sense_range=0)
        self.back_gate.set_limit(limit)
        self.back_gate.set_sense_function(function='i', sense_range=limit)

        print('Back gate, configure 2-point measurement')
        # Always use 2-point measurement for the gate
        self.back_gate.remote_sense(False)

        self.back_gate.set_integration_time(nplc)
        # self.back_gate.set_voltage(0)
        self.back_gate.set_output_level(0)
        print('Turn out output of backgate')
        self.back_gate.output_state(True)

        # TEST WITH AZERO BOTH TRUE AND FALSE!!!!
        # self.back_gate.set_auto_zero('v', True)
        # self.back_gate.set_auto_zero('i', True)
        # self.back_gate.auto_zero_now()

    def _configure_source(
        self, function, source_range, limit, nplc, remote_sense=False
    ):
        """
        Configure souce-drain as a voltage source
        """
        self.source.reset_instrument()
        self.source.use_rear_terminals()

        # Ok, for new we just go with defbuffer1... I still think it
        # would be cool to make a dedicated buffer, but it can wait...
        # self.source.make_buffer('iv_data', 10)
        self.source.clear_buffer()

        if function.lower() == 'v':
            self.source.set_source_function('v', source_range=source_range)
            # Temporarily set sense to auto to avoid temporary range conflicts
            self.source.set_sense_function('i', sense_range=0)
            self.source.set_limit(limit)
            self.source.set_sense_function('i', sense_range=limit)
        else:
            self.source.set_source_function('i', source_range=source_range)
            # Temporarily set sense to auto to avoid temporary range conflicts
            self.source.set_sense_function('v', sense_range=0)
            self.source.set_limit(limit)
            self.source.set_sense_function('v', sense_range=limit)
        self.source.set_output_level(0)

        self.source.set_integration_time(nplc)
        self.source.remote_sense(remote_sense)
        self.source.output_state(True)

        # TEST WITH AZERO BOTH TRUE AND FALSE!!!!
        self.source.set_auto_zero('v', True)
        self.source.set_auto_zero('i', True)
        self.source.auto_zero_now()

    """
    TODO:
    read_gate() and read_source() should be merged into a single funcion
    this will allow to first fire trigers for both source and gate, and
    then afterwards read the values and thus speed up overall aquisition time.
    """

    def read_gate(self):
        self.back_gate.trigger_measurement()
        reading = self.back_gate.read_latest()
        # Todo: Check status if device is in compliance
        data = {
            'v_backgate': reading['source_value'],
            'i_backgate': reading['value'],
        }
        self.add_to_current_measurement(data)
        return reading['source_value']

    def read_source(self, function='v', read_dmm=True):
        if read_dmm:
            v_total = self.dmm.read_dc_voltage()
        else:
            v_total = None

        self.source.trigger_measurement()
        reading = self.source.read_latest()
        # Todo: Check status if device is in compliance

        if function == 'v':
            v_xx = (reading['source_value'],)
            current = reading['value']
        else:
            v_xx = (reading['value'],)
            current = reading['source_value']

        data = {'v_xx': v_xx, 'current': current}
        if v_total is not None:
            data['v_total'] = v_total
        self.add_to_current_measurement(data)
        return reading['source_value']
