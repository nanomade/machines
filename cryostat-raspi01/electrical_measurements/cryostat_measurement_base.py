import json
import time
import socket

import Gpib  # linux-gpib, user space wrapper to kernel driver

from PyExpLabSys.drivers.keithley_2000 import Keithley2000
from PyExpLabSys.drivers.keithley_2450 import Keithley2450
from PyExpLabSys.drivers.keithley_6220 import Keithley6220
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
    'v_xy': [],
    'dv_di': [],
    'theta': [],
    'v_backgate': [],
    'i_backgate': [],
    'v_frontgate': [],
    'i_frontgate': [],
    'b_field': [],
    'vti_temp': [],
    'sample_temp': [],
}


class CryostatMeasurementBase(object):
    def __init__(self):
        self.current_measurement = CURRENT_MEASUREMENT_PROTOTYPE.copy()

        self.current_source = Keithley6220(interface='lan', path='192.168.0.3')
        self.back_gate = Keithley2450(interface='lan', device='192.168.0.30')
        self.front_gate = Keithley2450(interface='lan', device='192.168.0.31')
        self.dmm = Keithley2000(
            interface='serial',
            device='/dev/serial/by-id/usb-FTDI_Chipi-X_FT6EYK1T-if00-port0',
            baudrate=9600,
        )

        # TODO: Currently we trig all instruments; we should aim towards
        # trigging only the ones we will actually use
        self.back_gate.configure_digital_port_as_triggers()

        self.lock_in = None  # Used for AC measurements

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(1)
        self.sock.settimeout(1.0)

        # self.chamber_name = 'cryostat'
        self.chamber_name = 'dummy'

        self.lock_in_frequency = None
        # self.set_lock_in_frequency(1010)  # Only on the AC measurements
        self.data_set_saver = DataSetSaver("measurements_" + self.chamber_name,
                                           "xy_values_" + self.chamber_name,
                                           credentials.user, credentials.passwd)
        self.data_set_saver.start()

    def _identify_all_instruments(self):
        raise NotImplementedError

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

    def _read_cryostat(self):
        field = self._read_socket('cryostat_magnetic_field#json')
        vti_temp = self._read_socket('cryostat_vti_temperature#json')
        sample_temp = self._read_socket('cryostat_sample_temperature#json')
        data = {
            'b_field': field,
            'vti_temp': vti_temp,
            'sample_temp': sample_temp,
        }
        if None not in data.values():
            self.add_to_current_measurement(data)

    def _configure_back_gate(self):
        # Todo: take limit as an argument
        # Todo: abstriact this to configure either front or back gate
        self.back_gate.set_source_function('v')
        self.back_gate.set_current_limit(1e-5)
        self.back_gate.set_voltage(0)
        self.back_gate.output_state(True)
        print('Read latest value from back gate (verify read works)')
        self.back_gate.trigger_measurement()
        data = self.back_gate.read_latest()
        print(data)

    def set_lock_in_frequency(self, frequency: float):
        # Will be re-implemented in AC classes
        raise NotImplementedError

    def reset_current_measurement(self, measurement_type, error=False):
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

    def _add_metadata(self,
                      labels, meas_type, comment, timestep=None,
                      freq=None, current=None, delta_i=None,
                      nplc=None):
        metadata = {
            'Time': CustomColumn(time.time(), "FROM_UNIXTIME(%s)"),
            'label': None,
            'type': meas_type,
            'current': current,
            'comment': comment,
            'nplc': nplc,
            'timestep': timestep,
            'frequency': freq,
            'delta_i': delta_i,
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
        Check that current source is operating as expected
        if not, the measurement has to be stopped.
        """
        source_ok = self.current_source.read_status()
        if not source_ok:
            print('ABORT DUE TO COMPLIENCE')
            self.reset_current_measurement(None, error=True)
            # TODO - execute only the relevant stop function
            self.current_source.stop_and_unarm_sweep()
            self.current_source.stop_and_unarm_wave()
            self.current_source.set_current(0)
            self.current_source.output_state(False)
            print(self.current_source.latest_error)
        return source_ok

    def _calculate_steps(self, start, stop, steps, step_type='linear'):
        delta_current = stop - start
        step_size = delta_current / (steps - 1)
        step_list = []
        for i in range(0, steps):
            current = start + step_size * i
            step_list.append(current)
        # yield?
        return step_list

    def read_gate(self, store_data=True):
        # voltage, current = self.back_gate.read_volt_and_current()
        self.back_gate.trigger_measurement()
        data = self.back_gate.read_latest()

        # EXECUTE TRIGGER - THIS CAN NOW BE DONE MORE IN A MORE CLEVER
        # WAY, BUT TO GET STARTET WE JUST EMULATE OLD BEHAVIOUR
        self.back_gate.instr.write('*TRG')

        if not store_data:
            # This is just misuse to start a trigger
            return data['v_backgate']
        # current = self.back_gate.read_current()
        data = {
            'v_backgate': data['source_value'],
            'i_backgate': data['value']
        }
        self.add_to_current_measurement(data)
        return data['v_backgate']

    def dummy_background_measurement(self):
        # This should be a simple measurement that runs
        # when nothing else is running and allowing to
        # show status data such as current and DMM voltage
        # in the frontend
        pass

    # This will move into its own class - not to be used from here
    # def gated_ac_4_point_measurement(
    #         self,
    #         i_start: float, i_stop: float, total_i_steps: int,
    #         backgate_from, backgate_to, gate_steps
    # ):
    #     """
    #     Perform a gated 4-point AC iv-measurement.
    #     :param i_start: The lowest current in the sweep.
    #     :param i_stop: The highest current in the sweep.
    #     :param total_i_steps: Number of steps in the sweep.
    #     :param backgate_from:
    #     :param backgate_to:
    #     :param gate_steps:
    #     """
    #     labels = {
    #         'v_total': 'Vtotal', 'v_sample': 'Vsample',
    #         'current': 'Current', 'theta': 'Theta',
    #         'v_backgate': 'Back Gate Voltage', 'i_backgate': 'Back Gate Leak'
    #     }
    #     self._add_metadata(labels, 203, 'Gated AC measurement',
    #                        freq=self.lock_in_frequency)

    #     self.reset_current_measurement('gated_ac_sweep')

    #     # Todo: Set correct ranges for compliance and source
    #     self.back_gate.set_source_function('v')
    #     self.back_gate.set_current_limit(1e-4)
    #     self.back_gate.set_voltage(backgate_from)
    #     self.back_gate.output_state(True)
    #     time.sleep(0.1)
    #     self.read_gate()

    #     gate_steps = self._calculate_steps(backgate_from, backgate_to, gate_steps)

    #     self._init_ac(i_start, i_stop)  # Configure current source
    #     current_steps = self._calculate_steps(i_start, i_stop, total_i_steps)

    #     for gate_v in gate_steps:
    #         if self.current_measurement['type'] is None:
    #             continue
    #         self.back_gate.set_voltage(gate_v)
    #         time.sleep(0.5)
    #         self.read_gate()

    #         t = threading.Thread(target=self._ac_4_point_sweep,
    #                              args=(current_steps,))
    #         t.start()
    #         while t.is_alive():
    #             if self.current_measurement['type'] is None:
    #                 # Measurement has been aborted
    #                 t.stop()

    #             # Backgate can be measured slower than the inner sweep,
    #             # we do it periodically while waiting for the sweep
    #             print('waiting')
    #             time.sleep(1)
    #             self.read_gate()
    #         self.read_gate()

    #     # TODO!! Handle the case of non-succes!
    #     # if self.current_measurement['error']:

    #     # Indicate that the measurment is completed
    #     self.current_source.stop_and_unarm()
    #     self.back_gate.set_voltage(0)
    #     self.back_gate.output_state(False)
    #     self.reset_current_measurement(None)


if __name__ == '__main__':
    pass
