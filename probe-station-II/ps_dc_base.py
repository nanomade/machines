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

    def _configure_back_gate(self, source_range, current_limit, nplc):
        """
        Configure the 2450 for gating.
        """
        self.back_gate.clear_buffer('gate_data')
        self.back_gate.set_source_function(function='v', source_range=source_range)
        # Temporarily set sense to auto to avoid temporary range conflicts
        self.back_gate.set_sense_function(function='i', sense_range=0)
        self.back_gate.set_current_limit(current_limit)
        self.back_gate.set_sense_function(function='i', sense_range=current_limit)
        self.back_gate.set_integration_time(nplc)
        self.back_gate.set_voltage(0)
        self.back_gate.output_state(True)

        # TEST WITH AZERO BOTH TRUE AND FALSE!!!!
        self.back_gate.set_auto_zero('v', True)
        self.back_gate.set_auto_zero('i', True)
        self.back_gate.auto_zero_now()

    def _configure_source(self, source_range, current_limit, nplc):
        """
        Configure souce-drain as a voltage source
        """
        self.source.clear_buffer('iv_data')
        self.source.set_source_function('v', source_range=source_range)
        # Temporarily set sense to auto to avoid temporary range conflicts
        self.source.set_sense_function('i', sense_range=0)
        self.source.set_current_limit(current_limit)
        self.source.set_sense_function('i', sense_range=current_limit)
        self.source.set_integration_time(nplc)
        self.source.set_voltage(0)
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
        self.back_gate.trigger_measurement(buffer='gate_data')
        reading = self.back_gate.read_latest(buffer='gate_data')
        # Todo: Check status if device is in compliance
        data = {
            'v_backgate': reading['source_value'],
            'i_backgate': reading['value'],
        }
        self.add_to_current_measurement(data)
        return reading['source_value']

    def read_source(self, nplc=None, read_dmm=True):
        if read_dmm:
            v_total = self.dmm.read_dc_voltage()
        else:
            v_total = None

        self.source.trigger_measurement(buffer='iv_data')
        reading = self.source.read_latest(buffer='iv_data')
        # Todo: Check status if device is in compliance
        data = {
            # 'v_total': v_total,
            'v_xx': reading['source_value'],
            'current': reading['value'],
        }
        if v_total is not None:
            data['v_total'] = v_total
        self.add_to_current_measurement(data)
        return reading['source_value']
