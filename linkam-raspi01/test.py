from PyExpLabSys.drivers.vaisala_dmt143 import VaisalaDMT143
from PyExpLabSys.drivers.keithley_2400 import Keithley2400
from PyExpLabSys.drivers.keithley_2700 import Keithley2700


class LinkamTest(object):
    def __init__(self):
        self.dew_point = VaisalaDMT143(port='/dev/ttyUSB0')

        self.gate = Keithley2400(interface='gpib', gpib_address=22)
        self.source = Keithley2400(interface='gpib', gpib_address=24)
        self.switch_unit = Keithley2700(interface='gpib', gpib_address=5)

        print(self.switch_unit.read_software_version())
        
        # self.switch_unit.scpi_comm(':ROUT:MULT:CLOS (@219,205,250)')
        print(self.switch_unit.scpi_comm('ROUT:Mult:CLOS?'))
        # ROUTe:MULTiple:CLOSe:STATe? <clist>
        # self.gate.scpi_comm('SOURCE:VOLTage:RANGe 20')
        # self.gate.scpi_comm('SENSe:VOLTage:RANGe 20')
        # print(self.gate.scpi_comm('SOURCE:VOLTage:RANGe?'))
        # print(self.gate.scpi_comm('SENSe:VOLTage:RANGe?'))
        # print(self.source.scpi_comm('SENSe:VOLTage:RANGe?'))
        # exit()

    def test(self):
        dp = self.dew_point.water_level()

        self.source.set_current_limit(0.01)
        # self.source.set_current_range(stop)
        # self.gate.set_voltage_limit(10)
        self.source.set_voltage(0.2)
        self.source.output_state(True)

        self.gate.set_current_limit(1e-6)
        self.gate.set_voltage_limit(10)
        self.gate.set_voltage(-1.0)
        self.source.output_state(True)

        # # Configuration A
        # self.switch_unit.scpi_comm(':ROUT:OPEN:ALL')
        self.switch_unit.scpi_comm(':ROUT:MULT:CLOSE (@219,205,250)')
        volt_2p, _, _ = self.switch_unit.read()
        print()
        print('Dew point is: {}'.format(dp['dew_point']))
        print('2-point voltage: {:.1f}mV'.format(volt_2p * 1000))

        print('Gate. V: {:.1f}mV, Current: {:.1f}uA'.format(
            self.gate.read_voltage() * 1000,
            self.gate.read_current() * 1e6
        ))

        print('source. V: {:.1f}mV, Current: {:.3f}uA'.format(
            self.source.read_voltage() * 1000,
            self.source.read_current() * 1e6
        ))


if __name__ == '__main__':
    LT = LinkamTest()
    LT.test()
