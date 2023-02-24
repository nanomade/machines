import time
import json
import socket
# import logging

import Gpib  # linux-gpib, user space wrapper to kernel driver

from PyExpLabSys.drivers.srs_sr830 import SR830
from PyExpLabSys.drivers.keithley_2000 import Keithley2000
from PyExpLabSys.drivers.keithley_2400 import Keithley2400
# Todo: Check why CustomColumn is needed???
from PyExpLabSys.common.database_saver import DataSetSaver, CustomColumn

import credentials


CURRENT_MEASUREMENT_PROTOTYPE = {
    'type': None,  # DC-sweep, AC-sweep
    'error': None,
    'start_time': 0,
    'current_time': 0,
    'dew_point': [],
    'theta_1': [],
    'theta_2': [],
    'current_1': [],
    'current_2': [],
    'lock_in_v1': [],
    'lock_in_v2': [],
    'v_backgate': [],  # Back gate voltage
    'i_backgate': []  # Bakc gate leak-current
}


class LinkamMeasurementBase(object):
    def __init__(self, init_current_loggers=False):
        self.current_measurement = CURRENT_MEASUREMENT_PROTOTYPE.copy()
        self.lock_in_1 = SR830(interface='gpib', gpib_address=7)
        self.lock_in_2 = SR830(interface='gpib', gpib_address=6)
        self.back_gate = Keithley2400(interface='gpib', gpib_address=24)

        self.source_logger_1 = Keithley2000(interface='gpib', gpib_address=14)
        self.source_logger_2 = Keithley2000(interface='gpib', gpib_address=15)
        if init_current_loggers:
            self.source_logger_1.read_ac_voltage()
            self.source_logger_1.scpi_comm(':INITiate:CONTinuous ON')
            self.source_logger_1.scpi_comm('TRIGGER:SOURCE IMM')
            self.source_logger_2.read_ac_voltage()
            self.source_logger_2.scpi_comm(':INITiate:CONTinuous ON')
            self.source_logger_2.scpi_comm('TRIGGER:SOURCE IMM')

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(1)
        self.sock.settimeout(1.0)

        self.chamber_name = 'linkam'
        # self.chamber_name = 'dummy'
        self.aborted = False
        self._restart_data_set_saver()

    def _restart_data_set_saver(self):
        self.data_set_saver = DataSetSaver("measurements_" + self.chamber_name,
                                           "xy_values_" + self.chamber_name,
                                           credentials.user, credentials.passwd)
        self.data_set_saver.start()

    # Todo, take arguments to check only the needed instruments, or
    # check each instrument but report error only if it is not None
    def _identify_all_instruments(self):
        found_all = True
        try:
            lock_in_1_id = self.lock_in_1.read_software_version()
        except Gpib.gpib.GpibError:
            lock_in_1_id = ''
        if lock_in_1_id.find('SR830') > 0:
            print('Found SRS 830 at GPIB 7. Lock-In amplifier')
        else:
            print('Did NOT find SR830 at GPIB 7 - LockIn 1 missing!!!!!!')
            found_all = False

        try:
            lock_in_2_id = self.lock_in_2.read_software_version()
        except Gpib.gpib.GpibError:
            lock_in_2_id = ''
        if lock_in_2_id.find('SR830') > 0:
            print('Found SRS 830 at GPIB 6. Lock-In amplifier')
        else:
            print('Did NOT find SR830 at GPIB 6 - LockIn 2 missing!!!!!!')
            found_all = False

        try:
            source_logger_1_id = self.source_logger_1.read_software_version()
        except Gpib.gpib.GpibError:
            source_logger_1_id = ''
        if source_logger_1_id.find('MODEL 2000') > 0:
            print('Found Keithley 2000 at GPIB 14. source_logger_1')
            # pass
        else:
            print('Did NOT find Keithley 2000 at GPIB 14, no source_logger_1!!!')
            found_all = False

        try:
            source_logger_2_id = self.source_logger_2.read_software_version()
        except Gpib.gpib.GpibError:
            source_logger_2_id = ''
        if source_logger_2_id.find('MODEL 2000') > 0:
            print('Found Keithley 2000 at GPIB 15. source_logger_2')
            # pass
        else:
            print('Did NOT find Keithley 2000 at GPIB 15, no source_logger_2!!!')
            found_all = False

        try:
            back_gate_id = self.gate.read_software_version()
        except Gpib.gpib.GpibError:
            back_gate_id = ''
        if back_gate_id.find('MODEL 2400') > 0:
            print('Found Keithley 2400 at GPIB 22. Use for Gate')
            pass
        else:
            print('Did NOT find Keithley 2400!!! No Gate!!!')
            found_all = False
        return found_all

    def _scan_gpib(self):
        for i in range(0, 30):
            device = Gpib.Gpib(0, pad=i)
            try:
                device.write('*IDN?')
            except Gpib.gpib.GpibError:
                continue
            reply = device.read()
            print('{}: {}'.format(i, reply))

    def _read_gate(self):
        voltage = self.back_gate.read_voltage()
        current = self.back_gate.read_current()
        data = {'v_backgate': voltage, 'i_backgate': current}
        self.add_to_current_measurement(data)
        return current

    def _read_current_sources(self):
        current_1 = self.source_logger_1.next_reading() / 1e6
        current_2 = self.source_logger_2.next_reading() / 1e6

        data = {'current_1': current_1, 'current_2': current_2}
        self.add_to_current_measurement(data)
        return current_1, current_2

    def _read_lock_ins(self):
        v_1, theta_1, _ = self.lock_in_1.read_r_and_theta()  # ~35ms
        v_2, theta_2, _ = self.lock_in_2.read_r_and_theta()  # ~35ms

        data = {
            'lock_in_v1': v_1, 'lock_in_v2': v_2,
            'theta_1': theta_1, 'theta_2': theta_2,
        }
        self.add_to_current_measurement(data)

    def _read_vaisala(self):
        cmd = 'h20_concentration_linkam#json'.encode()
        self.sock.sendto(cmd, ('127.0.0.1', 9001))
        recv = self.sock.recv(65535)
        data = json.loads(recv)
        value = data[1]
        data = {'h20_concentration': value}
        self.add_to_current_measurement(data)

    def _prepare_gate(self, compliance):
        self.back_gate.set_source_function('v')
        self.back_gate.set_current_limit(compliance)
        self.back_gate.set_voltage(0)
        self.back_gate.output_state(True)
        time.sleep(1)
        return True

    def _step_measure(self, steps, time_pr_step):
        for step in steps:
            if self.aborted:
                return False
            # print('Step loop was', time.time() - t_step_start, step)
            t_step_start = time.time()
            self.back_gate.set_voltage(step)  # ~5ms
            self._read_gate()  # ~200ms - why so slow?

            dt = time.time() - t_step_start
            if dt < time_pr_step:
                time.sleep(time_pr_step - dt)
            self._read_lock_ins()
        return True

    def _add_metadata(self, labels, meas_type, comment, timestep=None, freq=None):
        try:
            # Test if sql-connection is still alive
            self.data_set_saver.get_unique_values_from_measurements('type')
        except self.data_set_saver.MySQLdb._exceptions.OperationalError:
            self._restart_data_set_saver()

        timestamp = CustomColumn(time.time(), "FROM_UNIXTIME(%s)")
        for key, value in labels.items():
            metadata = {
                'Time': timestamp,
                'label': None,
                'type': meas_type,
                'comment': comment,
                'timestep': timestep,
                'frequency': freq
            }

            if isinstance(value, str):
                metadata.update({'label': value})
            else:  # value is dict
                metadata.update(value)

            self.data_set_saver.add_measurement(key, metadata)
        return True

    def instrument_id(self):
        found_all = self._identify_all_instruments()
        if not found_all:
            self._scan_gpib()

    def reset_current_measurement(self, measurement_type, error=False):
        """
        Reset current data if a new measurement is about to start.
        If measurement_type is None, this indicates that the measurement
        stops, in this case keep the data for now.
        """
        if measurement_type is None:
            self.current_measurement['type'] = None
            self.current_measurement['type'] = error
        else:
            for key, value in self.current_measurement.items():
                if isinstance(value, list):
                    self.current_measurement[key].clear()
            self.current_measurement.update(
                {
                    'type': measurement_type,
                    'start_time': time.time(),
                    'current_time': time.time()
                }
            )
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

    def abort_measurement(self):
        # self.reset_current_measurement(None, error='Aborted')
        # As minimum, implementation should set self.aborted to True
        raise NotImplementedError


if __name__ == '__main__':
    Base = LinkamMeasurementBase()
    # Base._identify_all_instruments()
    Base._scan_gpib()
