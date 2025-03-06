import json
import time
import socket

import numpy as np

from PyExpLabSys.drivers.keithley_2100 import Keithley2100
from PyExpLabSys.drivers.keithley_2450 import Keithley2450

# Todo: Check why CustomColumn is needed???
from PyExpLabSys.common.database_saver import DataSetSaver, CustomColumn

import credentials


CURRENT_MEASUREMENT_PROTOTYPE = {
    'type': None,  # DC-sweep, AC-sweep
    'error': None,
    'start_time': 0,
    'current_time': 0,
    'current': [],
    'v_total': [],
    'v_xx': [],
    'v_backgate': [],  # Back gate voltage
    'i_backgate': [],  # Bakc gate leak-current
}


class ProbeStationMeasurementBase(object):
    def __init__(self):
        self.current_measurement = CURRENT_MEASUREMENT_PROTOTYPE.copy()
        self.tsp_link =  Keithley2450(interface='lan', hostname='192.168.0.3')
        self.tsp_link.instr.timeout = 10000

        self.dmm = Keithley2100(
            interface='usbtmc', visa_string='USB::0x05E6::0x2100::INSTR'
        )
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(1)
        self.sock.settimeout(1.0)

        # self.chamber_name = 'probe_station_ii'
        self.chamber_name = 'dummy'

        self.data_set_saver = DataSetSaver(
            "measurements_" + self.chamber_name,
            "xy_values_" + self.chamber_name,
            credentials.user,
            credentials.passwd,
        )
        self.data_set_saver.start()

    def _read_socket(self, cmd):
        try:
            self.sock.sendto(cmd.encode(), ('127.0.0.1', 9000))
            recv = self.sock.recv(65535)
            data = json.loads(recv)
            value = data[1]
        except socket.timeout:
            print('Lost access to socket')
            value = None
        return value

    def prepare_tsp_triggers(self):
        preparescript = """
        -- Prepare trigger to accept TSP-triggers
        tsplink.initialize()
        trigger.model.load("Empty")
        node[2].trigger.model.load("Empty")
        tsplink.line[1].reset()
        tsplink.line[1].mode = tsplink.MODE_SYNCHRONOUS_MASTER
        tsplink.line[2].mode = tsplink.MODE_SYNCHRONOUS_ACCEPTOR
        trigger.tsplinkout[1].stimulus = trigger.EVENT_NOTIFY1
        trigger.tsplinkin[2].clear()
        trigger.tsplinkin[2].edge = trigger.EDGE_RISING

        node[2].tsplink.line[2].mode = node[2].tsplink.MODE_SYNCHRONOUS_MASTER
        node[2].tsplink.line[1].mode = node[2].tsplink.MODE_SYNCHRONOUS_ACCEPTOR
        node[2].trigger.tsplinkout[2].stimulus = node[2].trigger.EVENT_NOTIFY2
        node[2].trigger.tsplinkin[1].clear()
        node[2].trigger.tsplinkin[1].edge = node[2].trigger.EDGE_RISING

        -- Build actual trigger model
        trigger.model.setblock(1, trigger.BLOCK_NOTIFY, trigger.EVENT_NOTIFY1)
        trigger.model.setblock(2, trigger.BLOCK_MEASURE_DIGITIZE)

        node[2].trigger.model.setblock(1, node[2].trigger.BLOCK_WAIT, node[2].trigger.EVENT_TSPLINK1)
        node[2].trigger.model.setblock(2, node[2].trigger.BLOCK_MEASURE_DIGITIZE)
        """
        self.tsp_link.load_script('preparescript', preparescript)
        self.tsp_link.execute_script('preparescript')
        return
    
    def configure_dmm(self, v_limit):
        """
        Configure  Model 2000 used for 2-point measurement
        The unit is set up to measure on the buffered output of
        the 2450.
        """
        self.dmm.configure_measurement_type('volt:dc')
        self.dmm.set_range(v_limit)
        self.dmm.set_integration_time(2)
        self.dmm.scpi_comm(':INIT:CONT ON')  # TODO: Add this to driver
    
    def reset_current_measurement(
        self, measurement_type, error=False, keep_measuring=False
    ):
        """
        Reset current data if a new measurement is about to start.
        If measurement_type is None, this indicates that the measurement
        stops, in this case keep the data for now.
        """
        if measurement_type is None:
            self.current_measurement['type'] = None
            self.current_measurement['error'] = error
        else:
            for key, value in self.current_measurement.items():
                if isinstance(value, list):
                    self.current_measurement[key].clear()
            if not keep_measuring:
                self.current_measurement.update(
                    {
                        'type': measurement_type,
                        'start_time': time.time(),
                        'current_time': time.time(),
                    }
                )
            else:
                self.current_measurement.update({'type': measurement_type})

        return True

    def add_to_current_measurement(self, data_point: dict):
        """
        Here we store the data, both permenantly in the database
        and temporarely in the local dict self.current_measurement
        """
        now = time.time() - self.current_measurement['start_time']
        for key in self.current_measurement.keys():
            if key in data_point:
                value = data_point[key]
                self.current_measurement[key].append((now, value))
                self.data_set_saver.save_point(key, (now, value))
        self.current_measurement['current_time'] = time.time()

    def _add_metadata(
        self,
        labels,
        meas_type,
        comment,
        nplc=None,
        limit=None,
        steps=None,
        repeats=None,
    ):
        metadata = {
            'Time': CustomColumn(time.time(), "FROM_UNIXTIME(%s)"),
            'label': None,
            'type': meas_type,
            'comment': comment,
            'nplc': nplc,
            'limit': limit,
            'steps': steps,
            'repeats': repeats,
        }
        for key, value in labels.items():
            metadata.update({'label': value})
            self.data_set_saver.add_measurement(key, metadata)
        return True

    def abort_measurement(self):
        print('ABORT')
        self.reset_current_measurement(None, error='Aborted')

    def _check_I_source_status(self):
        """
        Check that source is not in compliance. If it is, the system
        shoudl be stopped (or not depending on configuration).
        """
        # Here we should check variables as set by _read_gate() and
        # _read_source, and stop the measurement if appropriate

        # :OUTPut[1]:INTerlock:TRIPped?

        source_ok = True
        return source_ok

    def _ramp_gate(self, v_from, v_to, rate=0.5, force_even_if_abort=False):
        # Rate is the allowed gate-sweep rate in V/s
        # todo: strongly consider to move this up to dc_base
        sign = np.sign(v_to - v_from)
        if sign == 0:
            self.tsp_link.set_output_level(0, node=1)
            return
        step_size = 0.025

        if abs(v_to - v_from) < 3 * step_size:
            # This is not really a ramp, this is a continous sweep that we can
            # accept to performin one go:
            msg = 'Small step, set gate directly: {:.1f}mV'
            print(msg.format(1000 * abs(v_to - v_from)))
            # self.back_gate.set_voltage(v_to)
            self.tsp_link.set_output_level(v_to, node=1)
            return

    # This code is also used in the Linkham code
    def _calculate_steps(self, v_low, v_high, steps, repeats=1, **kwargs):
        """
        Calculate a set gate steps.
        Consider to move to a common library since so many setups use it
        **kwargs used only to eat extra arguments from network syntax
        """
        delta = v_high - v_low
        step_size = delta / (steps - 1)

        if repeats == 0:
            v_start = v_low
        else:
            v_start = 0

        # From 0 to v_high
        up = list(np.arange(v_start, v_high, step_size))
        # v_high -> 0
        down = list(np.arange(v_high, v_start, -1 * step_size))

        # N * (v_high -> v_low -> v_high)
        zigzag = (
            list(np.arange(v_high, v_low, -1 * step_size))
            + list(np.arange(v_low, v_high, step_size))
        ) * repeats
        step_list = up + zigzag + down + [0]
        return step_list

    def _configure_instruments(self, source, gate, params):
        print('Configure tsp-instruments')
        self.prepare_tsp_triggers()

        gate_range = max(abs(gate['v_low']), abs(gate['v_high']))
        if 'v_low' in source:
            source_range = max(abs(source['v_high']), abs(source['v_low']))
            source_function = 'v'
            sense_function = 'i'
        else:
            source_range = max(abs(source['i_high']), abs(source['i_low']))
            source_function = 'i'
            sense_function = 'v'
        
        # TODO!!!! THIS REALLY NEED TO GO INTO ps_measurements_base - the code
        # is essentially the same for both measurement modes!
        self.tsp_link.clear_output_queue()
        self.tsp_link.use_rear_terminals(node=1)
        self.tsp_link.use_rear_terminals(node=2)

        self.tsp_link.set_source_function(function='v', source_range=gate_range, node=1)
        # Temporarily set sense to auto to avoid temporary range conflicts
        self.tsp_link.set_sense_function(function='i', sense_range=0, node=1)
        
        self.tsp_link.set_limit(gate['limit'], node=1)
        self.tsp_link.set_sense_function(function='i', sense_range=gate['limit'], node=1)
        # Always use 2-point measurement for the gate
        self.tsp_link.remote_sense(False, node=1)
        self.tsp_link.set_integration_time(nplc=gate['nplc'], node=1)

        self.tsp_link.set_source_function(source_function, source_range=source_range, node=2)
        # Temporarily set sense to auto to avoid temporary range conflicts
        self.tsp_link.set_sense_function(sense_function, sense_range=0, node=2)
        self.tsp_link.set_limit(source['limit'], node=2)
        self.tsp_link.set_sense_function(sense_function, sense_range=source['limit'], node=2)
        self.tsp_link.set_integration_time(nplc=source['nplc'], node=2)
        
        for node in (1, 2):
            time.sleep(0.25)
            self.tsp_link.clear_buffer(node=node)
            self.tsp_link.set_readback(action=params['readback'], node=node)
            self.tsp_link.set_output_level(0, node=node)
            self.tsp_link.output_state(True, node=node)
            self.tsp_link.set_auto_zero(params['autozero'], node=node)
            self.tsp_link.auto_zero_now(node=node) 
            self.tsp_link.clear_buffer(node=node)

        # If remote sense is activated with output off, a warning is issued
        if 'v_low' in source:
            self.tsp_link.remote_sense(False, node=2)
        else:
            self.tsp_link.remote_sense(True, node=2)

        # Note: The model of running the trigger model with a single measurement
        # and repeatedly trigger seems to have an overhead of approximately ~0.3NPLC
        # compared to a fully configured trigger sweep
        execute_iteration = """
        node[2].trigger.model.initiate()
        trigger.model.initiate()
        waitcomplete()
        n = node[1].defbuffer1.endindex
        m = node[2].defbuffer1.endindex
        printbuffer(n, n, node[1].defbuffer1, node[1].defbuffer1.units, node[1].defbuffer1.sourcevalues)
        printbuffer(m, m, node[2].defbuffer1, node[2].defbuffer1.units, node[2].defbuffer1.sourcevalues)
        print("end " .. n .. " " .. m)
        """
        self.tsp_link.load_script('execute_iteration', execute_iteration)
        print('Configure done')
    
    def read(self, read_dmm=False):
        self.tsp_link.execute_script('execute_iteration')
        # This script always output exactly three lines
        gate = self.tsp_link.instr.read().strip().split(',')
        source = self.tsp_link.instr.read().strip().split(',')

        if 'Amp' in source[1]:
            current = float(source[0])
            v_xx =  float(source[2])
        else:
            current = float(source[2])
            v_xx =  float(source[0])
            
        
        # Control should always be 'end n m' with n and m both being the
        # current iteration number
        # Todo: Assert this...
        control = self.tsp_link.instr.read().strip()
        # print('Control is: ', control)
        # Todo: Check status if device is in compliance
        data = {
            'i_backgate': float(gate[0]),
            'v_backgate': float(gate[2]),
            'v_xx': v_xx,
            'current': current,
        }      

        # TODO! This needs to be trigger based - or at least software triggered before
        # the tsp script is executed
        if read_dmm:
            v_total = self.dmm.read_dc_voltage()
        else:
            v_total = None
        if v_total is not None:
            data['v_total'] = v_total

        self.add_to_current_measurement(data)
        return data

    def dummy_background_measurement(self):
        # This should be a simple measurement that runs
        # when nothing else is running and allowing to
        # show status data such as current and DMM voltage
        # in the frontend
        pass


if __name__ == '__main__':
    pass
