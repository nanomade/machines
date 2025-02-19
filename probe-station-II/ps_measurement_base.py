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
        self.back_gate = Keithley2450(interface='lan', hostname='192.168.0.3')
        self.source = Keithley2450(interface='lan', hostname='192.168.0.4')
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

    # Todo, take arguments to check only the needed instruments, or
    # check each instrument but report error only if it is not None
    def _identify_all_instruments(self):
        found_all = True
        back_gate_id = self.back_gate.read_software_version()
        if back_gate_id.find('2450') > 0:
            # print('Found Keithley 2450 at 192.168.0.3')
            pass
        else:
            print('Did NOT find model 2450 at 192.168.0.3!!!!!!')
            found_all = False

        source_id = self.source.read_software_version()
        if source_id.find('2450') > 0:
            # print('Found Keithley 2450 at 192.168.0.4')
            pass
        else:
            print('Did NOT find model 2450 at 192.168.0.4!!!!!!')
            found_all = False

        dmm_id = self.dmm.read_software_version()
        if dmm_id.find('MODEL 2100') > 0:
            # print('Found Keithley 2000 in USB port')
            pass
        else:
            print('Did NOT find Keithley 2100 in USB port!!!')
            found_all = False
        return found_all

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

    def dummy_background_measurement(self):
        # This should be a simple measurement that runs
        # when nothing else is running and allowing to
        # show status data such as current and DMM voltage
        # in the frontend
        pass


if __name__ == '__main__':
    pass
