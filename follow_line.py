#!/usr/bin/env python3.5
"""
Copyright © 2021 Ludovic
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy,
modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
https://github.com/Hakvic
"""
import time
import logging
import random

from smbus import SMBus
from time import sleep
from ev3dev2.port import LegoPort
from ev3dev2.sensor import INPUT_4

from ev3dev2.motor import MoveTank, OUTPUT_B, OUTPUT_C, speed_to_speedvalue, SpeedNativeUnits
from ev3dev2.sensor.lego import ColorSensor, UltrasonicSensor
from ev3dev2.sound import Sound

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
# file_handler = logging.FileHandler("debug.log")
# file_handler.setLevel(logging.DEBUG)
# logger.addHandler(file_handler)
logger.addHandler(handler)

in1 = LegoPort(INPUT_4)
in1.mode = 'other-i2c'
sleep(0.5)
bus = SMBus(6)
address = 0x54
lamp = [174, 193, 22, 2, 1]
bus.write_i2c_block_data(address, 0, lamp)


class Robot:
    def __init__(self):
        self.tank_drive = MoveTank(OUTPUT_C, OUTPUT_B)
        self.sensor_middle = ColorSensor("in1")
        self.sensor_left = ColorSensor("in2")
        self.sensor_right = ColorSensor("in3")
        # self.sensor_ultrasonic = UltrasonicSensor("in4")
        # self.sensor_ultrasonic.mode = "US-DIST-CM"
        self.sensor_middle.mode = "COL-REFLECT"
        self.sensor_left.mode = "COL-REFLECT"
        self.sensor_right.mode = "COL-REFLECT"
        self.target = 0
        self.run = True
        self.cross_count = 0
        self.integral = 0
        self.error = 0
        self.derivative = 0
        self.last_error = 0
        self.direction = ["left", "forward"]

    def pid(self, speed, kp, ki, kd):
        speed = speed_to_speedvalue(speed)
        speed_native_units = speed.to_native_units(self.tank_drive.left_motor)

        self.error = self.target - self.sensor_middle.value()
        self.integral += self.error
        self.derivative = self.error - self.last_error

        u = (kp * self.error) + (ki * self.integral) + (kd * self.derivative)
        left_speed = SpeedNativeUnits(speed_native_units - u)
        right_speed = SpeedNativeUnits(speed_native_units + u)
        # logger.debug("u: {}".format(u))
        # logger.debug("left speed: {}".format(left_speed))
        # logger.debug("right speed: {}".format(right_speed))
        self.last_error = self.error

        return left_speed, right_speed

    def turn(self):

        # logger.debug("before sensor 1: {}".format(self.sensor_middle.value()))
        # logger.debug("before sensor 2: {}".format(self.sensor_left.value()))
        # logger.debug("before sensor 3: {}".format(self.sensor_left.value()))
        # logger.debug("Turn")
        if self.sensor_left.value() < 20:
            # logger.debug("left stop")
            self.tank_drive.stop()
            if self.sensor_left.value() < 20 and not self.sensor_right.value() < 20:
                self.tank_drive.on(0, 10)
                while self.sensor_middle.value() > 20 or self.sensor_left.value() < 20:
                    # logger.debug("while LEFT")
                    # logger.debug("sensor middle: {}".format(self.sensor_middle.value()))
                    # logger.debug("sensor left: {}".format(self.sensor_left.value()))
                    self.tank_drive.on(0, 10)
            # logger.debug("sensor middle after while: {}".format(self.sensor_middle.value()))
            # logger.debug("sensor left after while: {}".format(self.sensor_left.value()))

        if self.sensor_right.value() < 20:
            # logger.debug("right stop")
            self.tank_drive.stop()
            if self.sensor_right.value() < 20 and not self.sensor_left.value() < 20:
                self.tank_drive.on(10, 0)
                while self.sensor_middle.value() > 20 or self.sensor_right.value() < 20:
                    # logger.debug("while RIGHT")
                    # logger.debug("sensor middle: {}".format(self.sensor_middle.value()))
                    # logger.debug("sensor right: {}".format(self.sensor_right.value()))
                    self.tank_drive.on(10, 0)
            # logger.debug("sensor middle after while: {}".format(self.sensor_middle.value()))
            # logger.debug("sensor right after while: {}".format(self.sensor_right.value()))

    """
    def cruiser(self, left_speed, right_speed):

        distance = self.sensor_ultrasonic.value() / 10
        if 25 >= distance > 20:
            left_speed = left_speed * 0.75
            right_speed = right_speed * 0.75
        elif 20 >= distance > 15:
            left_speed = left_speed * 0.5
            right_speed = right_speed * 0.5
        elif 15 >= distance > 10:
            left_speed = left_speed * 0.25
            right_speed = right_speed * 0.25
        elif distance <= 10:
            left_speed = 0
            right_speed = 0

        return left_speed, right_speed
    """

    def sign(self):

        sigs = 1
        data = [174, 193, 32, 2, sigs, 1]
        bus.write_i2c_block_data(address, 0, data)
        block = bus.read_i2c_block_data(address, 0, 20)
        signColor = block[7] * 256 + block[6]
        signWidth = block[13] * 256 + block[12]
        signHeight = block[15] * 256 + block[14]

        while signColor == 1 and signWidth > 50 and signHeight > 25:
            # left_speed = 0
            # right_speed = 0
            self.tank_drive.stop()
            self.run = False
            Sound().play_song((('D4', 'e3'), ('D4', 'e3')))
            time.sleep(1)
            block = bus.read_i2c_block_data(address, 0, 20)
            signColor = block[7] * 256 + block[6]
        self.run = True

    def crossing(self):

        if self.sensor_left.value() < 20 or self.sensor_right.value() < 20:
            logger.debug("stop croisement")
            self.tank_drive.stop()
            if self.sensor_left.value() < 20 and self.sensor_right.value() < 20 and self.sensor_middle.value() < 20:
                logger.debug("cross_direction: {}".format(self.direction[0]))
                logger.debug("liste avant: {}".format(self.direction))
                if self.direction[0] == "left":
                    self.direction.pop(0)
                    Sound().play_song((('D4', 'e3'), ('D4', 'e3')))  # turn left
                    self.tank_drive.on(0, 10)
                    while self.sensor_middle.value() > 20 or self.sensor_left.value() < 20:
                        self.tank_drive.on(0, 10)

                elif self.direction[0] == "forward":  # go forward
                    self.direction.pop(0)
                    self.tank_drive.on(10, 10)
                    Sound().play_song((('D4', 'e3'), ('D4', 'e3')))
                    while self.sensor_left.value() < 20 and self.sensor_right.value() < 20:
                        self.tank_drive.on(10, 10)

                elif self.direction[0] == "right":  # turn right
                    self.direction.pop(0)
                    self.tank_drive.on(10, 10)
                    Sound().play_song((('D4', 'e3'), ('D4', 'e3')))
                    while self.sensor_middle.value() > 20 or self.sensor_right.value() < 20:
                        self.tank_drive.on(10, 0)

        logger.debug("liste apres:  {}".format(self.direction))

    def stop(self):
        if self.sensor_left.value() < 10 and self.sensor_right.value() < 10 and self.sensor_middle.value() > 70:
            logger.debug("STOP")
            self.tank_drive.stop()
            self.run = False

    def main(self, speed, kp, ki, kd):
        Sound().play_song((('D4', 'e3'), ('D4', 'e3')))
        self.target = self.sensor_middle.value()
        logger.debug("target: {}".format(self.target))
        while self.run:
            left_speed, right_speed = self.pid(speed, kp, ki, kd)
            # left_speed, right_speed = self.cruiser(left_speed, right_speed)
            self.turn()
            self.crossing()
            self.tank_drive.on(left_speed, right_speed)
            self.sign()
            self.stop()
            # time.sleep(0.5)
