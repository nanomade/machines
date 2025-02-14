import time
import pyvisa as visa


class Keithley2450():
    def __init__(self, interface='lan', hostname=''):
        if interface == 'lan':
            visa_string = 'TCPIP0::{}::inst0::INSTR'.format(hostname)
        rm = visa.ResourceManager()
        self.instr = rm.open_resource(visa_string)

        cmd = 'smu.measure.displaydigits = smu.DIGITS_6_5'
        self.instr.write(cmd)
        
        
    def reset_instrument(self):
        self.instr.write('reset()')

    # def lcd_brightness(self, value):
    # display.lightstate = display.STATE_LCD_75
        
    def output_state(self, output_state: bool = None):
        """Turn the output on or off"""
        if output_state is not None:
            if output_state:
                self.instr.write('smu.source.output = smu.ON')
            else:
                self.instr.write('smu.source.output = smu.OFF')
        actual_state_raw = self.instr.query('print(smu.source.output)')
        actual_state = (actual_state_raw.find('smu.ON') > -1)
        return actual_state
    
    def set_source_function(self, function: str = None, source_range: float = None):
        if function.lower() in ('i', 'current'):
            self.instr.write('smu.source.func = smu.FUNC_DC_CURRENT')
        if function.lower() in ('v', 'voltage'):
            self.instr.write('smu.source.func = smu.FUNC_DC_VOLTAGE')

        if source_range is None:
            self.instr.write('self.smu.source.autorange = smu.OFF')
        else:
            cmd = 'smu.source.range = {}'.format(source_range)
            self.instr.write(cmd)

        # TODO - Readback currently hard-coded!
        self.instr.write('smu.source.readback = smu.ON')
            
        actual_function = self.instr.query('print(smu.source.func)')
        # TODO: PARSE THIS INTO ENUM OF VOLTAGE AND CURRENT
        return actual_function

    def remote_sense(self, action: bool = None):
        if action is not None:
            if action:
                self.instr.write('smu.measure.sense = smu.SENSE_4WIRE')
            else:
                self.instr.write('smu.measure.sense = smu.SENSE_2WIRE')
        actual_state = (
            self.instr.query('print(smu.measure.sense)').find('4WIRE') > -1
        )
        return actual_state
    
    def set_sense_function(self, function: str = None, sense_range: float = None):
        """
        Set the sense range, a value of None returns the current value without
        changing the actual value. A range value of 0 indicates auto-range.
        """
        # TODO:
        # Many other measurement functions exists, such as resistance, power
        # and math functions
        if function.lower() in ('i', 'current'):
            self.instr.write('smu.measure.func = smu.FUNC_DC_CURRENT')
        if function.lower() in ('v', 'voltage'):
            self.instr.write('smu.measure.func = smu.FUNC_DC_VOLTAGE')

        if sense_range == 0:
            self.instr.write('smu.measure.autorange = smu.ON')
        else:
            cmd = 'smu.measure.range = {}'.format(sense_range)
            self.instr.write(cmd)

        actual_function = self.instr.query('print(smu.measure.func)')
        # TODO: PARSE THIS INTO ENUM OF VOLTAGE AND CURRENT
        return actual_function

    # def set_auto_zero(self, function: str, action: bool = None):
    #     """
    #     Set auto-zero behaviour for a given function (voltage or current).
    #     Action can be 'on', 'off', or None
    #     """
    #     if function.lower() == 'i':
    #         scpi_function = 'CURRENT'
    #     elif function.lower() == 'v':
    #         scpi_function = 'VOLTAGE'
    #     else:
    #         raise Exception('Function not allowed: {}'.format(function))

    #     if action is not None:    
    #         if action:
    #             scpi_action = 'On'
    #         else:
    #             scpi_action = 'Off'

    #         if scpi_action is not None:
    #             cmd = ':SENSE:{}:AZERO {}'.format(scpi_function, scpi_action)
    #             self.scpi_comm(cmd)

    #     cmd = ':SENSE:{}:AZERO?'.format(scpi_function)
    #     reply = self.scpi_comm(cmd)
    #     return reply

    # def auto_zero_now(self):
    #     """
    #     Perform a single auto-zero
    #     """
    #     cmd = ':SENSE:AZERO:ONCE'
    #     self.scpi_comm(cmd)
    #     return True

    
    def set_limit(self, value: float):
        """
        Set the desired limit for voltage or current depending on current
        source function.
        TODO: Query the measure range to check if value is legal
        """
        cmd = 'print(smu.source.func)'
        source_func = self.instr.query(cmd)
        if source_func.find('VOLTAGE') > -1:
            cmd = 'smu.source.ilimit.level'
        else:
            cmd = 'smu.source.vlimit.level'
        if value is not None:
            limit_cmd = cmd + '={}'.format(value)
            self.instr.write(limit_cmd)
        return value

    # Compatibility function, could be removed
    def set_current_limit(self, current: float = None):
        cmd = 'smu.source.func = smu.FUNC_DC_VOLTAGE'
        self.instr.write(cmd)
        if current is not None:
            self.set_limit(value=current)
        return current

    def query_limit(self):
        """
        Query the current source limit
        """
        query_cmd = 'print(smu.source.ilimit.level)'
        print(query_cmd)
        limit = float(self.instr.query(query_cmd))
        return limit

    def buffer_exists(self, buffer: str):
        cmd = 'print({} == nil)'.format(buffer)
        buffer_exists = self.instr.query(cmd).strip() == 'false'
        return buffer_exists
    
    def make_buffer(self, buffer: str, size: int = 10):
        """
        Make a buffer of type FULL and fillmode continous
        @return: True if created, false if buffer was already present
        """
        if size < 10:
            return False

        if self.buffer_exists(buffer):
            return False
        
        # TODO: Check if STYLE_FULL actually makes sense
        cmd = '{} = buffer.make({}, buffer.STYLE_FULL)'.format(buffer, size)
        self.instr.write(cmd)

        cmd = '{}.fillmode = buffer.FILL_CONTINUOUS'.format(buffer_name)
        self.instr.write(cmd)
        return True
    
    def trigger_measurement(self, buffer='defbuffer1'):
        cmd = 'print(smu.measure.read({}))'.format(buffer)
        value = float(self.instr.query(cmd))
        return value

    def clear_buffer(self, buffer='defbuffer1'):
        if not self.buffer_exists(buffer):
            return False
        self.instr.write('{}.clear()'.format(buffer))
        return True
    
    # def elements_in_buffer(self, buffer='defbuffer1'):

    def read_latest(self, buffer):
        cmd = 'print({}.readings[{}.endindex])'.format(buffer, buffer)
        reading = float(self.instr.query(cmd))
        return reading


if __name__ == '__main__':
    # addr = 'TCPIP0::192.168.0.3::inst0::INSTR'
    # print()
    hostname = '192.168.0.3'
    k = Keithley2450(interface='lan', hostname=hostname)

    k.set_source_function('i', 1)
    exit()
    
    # K.make_buffer('test', 50)

    
    print(
        k.instr.query(
            'print(test == nil)'
        )
    )
    exit()
    k.reset_instrument()
    k.trigger_measurement()
    exit()
    k.output_state(True)

    k.clear_buffer('test')

    t = time.time()
    for i in range(0, 20):
        print(k.trigger_measurement('test'), time.time() - t)

    # cmd = 'for x = 1, test.n do'
    n = int(k.instr.query('print(test.n)'))
    print('n is: ', n)
    for x in range(1, n + 1):
        cmd = 'printbuffer({}, {}, test, test.units, test.relativetimestamps)'.format(x, x)
        print(k.instr.query(cmd).strip())
    # cmd = 'end'

    
    # k.set_limit(1e-9)
    # print(k.query_limit())

    # k.make_buffer('test', 50)
    # k.trigger_measurement('test')
    
    # def set_auto_zero(self, function: str, action: bool = None):
    #     """
    #     Set auto-zero behaviour for a given function (voltage or current).
    #     Action can be 'on', 'off', or None
    #     """
    #     if function.lower() == 'i':
    #         scpi_function = 'CURRENT'
    #     elif function.lower() == 'v':
    #         scpi_function = 'VOLTAGE'
    #     else:
    #         raise Exception('Function not allowed: {}'.format(function))

    #     if action is not None:    
    #         if action:
    #             scpi_action = 'On'
    #         else:
    #             scpi_action = 'Off'

    #         if scpi_action is not None:
    #             cmd = ':SENSE:{}:AZERO {}'.format(scpi_function, scpi_action)
    #             self.scpi_comm(cmd)

    #     cmd = ':SENSE:{}:AZERO?'.format(scpi_function)
    #     reply = self.scpi_comm(cmd)
    #     return reply

    # def auto_zero_now(self):
    #     """
    #     Perform a single auto-zero
    #     """
    #     cmd = ':SENSE:AZERO:ONCE'
    #     self.scpi_comm(cmd)
    #     return True

    # def remote_sense(self, action: bool = None):
    #     if action is not None:
    #         if action:
    #             scpi_action = 'On'
    #         else:
    #             scpi_action = 'Off'
    #         cmd = 'SENSE:{}:RSENSE {}'
    #         self.scpi_comm(cmd.format('VOLTAGE', scpi_action))
    #         self.scpi_comm(cmd.format('CURRENT', scpi_action))
    #         self.scpi_comm(cmd.format('RESISTANCE', scpi_action))
    #     cmd = 'SENSE:VOLTAGE:RSENSE?'
    #     reply = self.scpi_comm(cmd)
    #     return reply                           
    

    # def read_from_buffer(self, start, stop, buffer='defbuffer1'):
    #     data = []
    #     for i in range(start, stop + 1):
    #         # cmd = 'TRACE:DATA? {}, {}, "{}", {}'.format(start, stop, buffer, self.srp)
    #         cmd = 'TRACE:DATA? {}, {}, "{}", {}'.format(i, i, buffer, self.srp)
    #         raw = self.scpi_comm(cmd, expect_return=True)
    #         reading = self._parse_raw_reading(raw)
    #         data.append(reading)
    #     return data

