import time
import socket
import threading
import RPi.GPIO as GPIO

import PyExpLabSys.auxiliary.pid as PID

from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.sockets import DataPushSocket
from PyExpLabSys.common.sockets import DateDataPullSocket

DIRECTION_PIN = 23
ROTATE_PIN = 24


class VTIControl(threading.Thread):
    """Physically control VTI needle valve"""

    def __init__(self):
        threading.Thread.__init__(self)
        self.name = 'VTI control'
        self.daemon = True

        # ~12000 is a quarter of a turn
        self.pulses = 0
        self.step_direction = True  # -> Higer pressure
        self.rotation_speed = 0  # Steps / s
        # Configure the two gpio pins as outputs
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(DIRECTION_PIN, GPIO.OUT)
        GPIO.setup(ROTATE_PIN, GPIO.OUT)

    def set_direction(self, direction: bool):
        self.step_direction = direction
        if direction:
            GPIO.output(DIRECTION_PIN, GPIO.LOW)
        else:
            GPIO.output(DIRECTION_PIN, GPIO.HIGH)

    def _single_step(self):
        if abs(self.pulses) > 40000:
            print('Needle valve cannot turn any further')
            return False
        GPIO.output(ROTATE_PIN, GPIO.HIGH)
        time.sleep(0.001)
        GPIO.output(ROTATE_PIN, GPIO.LOW)
        time.sleep(0.001)
        if self.step_direction:
            self.pulses += 1
        else:
            self.pulses -= 1
        return True

    def turn_valve(self, steps: int, direction: bool):
        self.rotation_speed = 0
        self.set_direction(direction)
        for i in range(0, steps):
            result = self._single_step()
            if not result:
                break
        return result

    def set_rotation_speed(self, rotation_speed):
        if rotation_speed < 0.5:
            self.rotation_speed = 0
        elif rotation_speed > 100:
            self.rotation_speed = 100
        else:
            self.rotation_speed = rotation_speed

    def run(self):
        rotate_ok = True
        while rotate_ok:
            if self.rotation_speed > 0:
                wait_time = 1.0 / self.rotation_speed
                msg = 'Waiting for {}ms. Steps are: {}'
                # print(msg.format(wait_time * 1000, self.pulses))
                rotate_ok = self._single_step()
                time.sleep(wait_time)
            else:
                # print('Rotation is 0')
                time.sleep(1)


class VTIRegulator:
    def __init__(self):
        self.vti_control = VTIControl()
        self.vti_control.start()

        self.pullsocket = DateDataPullSocket(
            'PID status',
            ['pulses', 'p', 'i', 'rate'],
            timeouts=[3, 3, 3, 3],
            port=9000,
        )
        self.pullsocket.start()
        self.pushsocket = DataPushSocket('VTI Setpoint', action='enqueue')
        self.pushsocket.start()

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(1)

        # self.setpoint = 4
        self.pid = PID.PID(pid_p=8, pid_i=0.001, pid_d=0, p_max=100, p_min=-50)
        self.pid.update_setpoint(6)  # Default of 6 is never quite wrong

    def read_vti_pressure(self):
        network_adress = 'cryostat-raspi01.fys.clients.local.'
        command = 'cryostat_vti_pressure#raw'.encode()
        self.sock.sendto(command, (network_adress, 9000))
        received = self.sock.recv(1024)
        received = received.decode('ascii')
        value_raw = received.split(',')[1]
        value = float(value_raw)
        return value

    def _initial_exercise(self):
        steps = 5000
        pressure = self.read_vti_pressure()
        print('Pressure is: {}'.format(pressure))
        print('A little excercise might be a good idea')
        time.sleep(5)
        print('Turn {} steps open'.format(steps))
        self.vti_control.turn_valve(steps, True)
        time.sleep(5)
        print('And now, turn {} steps close'.format(steps))
        self.vti_control.turn_valve(steps, False)
        print('Now, wait 60s for pressure to stabalize a bit')
        for i in range(0, 60):
            time.sleep(1)
            pressure = self.read_vti_pressure()
            print('{}. Pressure is: {}'.format(i, pressure))

    def main(self):
        # self._initial_exercise()

        while True:
            time.sleep(2)
            qsize = self.pushsocket.queue.qsize()
            new_setpoint = None
            while qsize > 0:
                element = self.pushsocket.queue.get()
                qsize = self.pushsocket.queue.qsize()
                print(element)
                if element.get('cmd') == 'vti_setpoint':
                    try:
                        new_setpoint = float(element.get('setpoint'))
                    except ValueError:
                        pass

            if new_setpoint:
                self.pid.update_setpoint(new_setpoint)

            pressure = self.read_vti_pressure()
            rotation_speed = self.pid.wanted_power(pressure)

            p = self.pid.proportional_contribution()
            i = self.pid.integration_contribution()

            msg = 'P: {:.2f}. I: {:.2f} Pressure: {:.2f}. Speed: {:.2f}/s. Pulses: {}'
            print(msg.format(p, i, pressure, rotation_speed, self.vti_control.pulses))

            self.vti_control.set_direction(rotation_speed > 0)
            self.vti_control.set_rotation_speed(abs(rotation_speed))


if __name__ == '__main__':
    VTI_REG = VTIRegulator()
    VTI_REG.main()
